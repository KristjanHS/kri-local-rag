#!/usr/bin/env python3
"""E2E test configuration and fixtures."""

import logging
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import pytest

from backend.config import get_service_url
from backend.weaviate_client import close_weaviate_client, get_weaviate_client
from tests.conftest import get_integration_config, is_service_healthy

logger = logging.getLogger(__name__)

# When a containerized CLI call fails, dump these services' recent logs so the
# failure is actionable without a manual `docker compose logs` round-trip
# (P3 Step 7 — diagnostics & isolation). This e2e-tier conftest already shells
# out to `docker compose` for the live stack; the dump is on that same path.
# <!-- external-process-test-gate-override: e2e-tier conftest already drives docker compose -->
_DIAGNOSTIC_SERVICES = ("app", "weaviate", "ollama")
_DIAGNOSTIC_LOG_TAIL = 200

# docker-compose.yml + the run-id pointer written by `make test-up` (scripts/dev/test-env.sh).
_COMPOSE_FILE = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")
_RUN_ID_FILE = Path(__file__).resolve().parents[2] / ".run_id"


class ComposeContext(NamedTuple):
    """Which docker compose stack the e2e fixtures should drive.

    `make test-up` runs the stack under a run-id project (from ``.run_id``) with the
    ``test`` profile and an ``app-test`` service; the default project (``app`` service,
    no profile) is what `make stack-up` uses. e2e fixtures must REUSE an already-running
    test stack — starting a second default-project stack spawns a conflicting Weaviate
    that dies on cluster init (``could not init cluster state``) and forces a skip.
    """

    project: str | None  # COMPOSE_PROJECT_NAME to set (None = compose default)
    base: list[str]  # `docker compose -f ... [--profile test]`
    app_service: str  # "app-test" (active test stack) or "app" (default project)
    diagnostic_services: tuple[str, ...]


def _compose_env(project: str | None) -> dict[str, str]:
    """Process env with COMPOSE_PROJECT_NAME pinned to the target project (if any)."""
    env = os.environ.copy()
    if project:
        env["COMPOSE_PROJECT_NAME"] = project
    return env


@lru_cache(maxsize=1)
def _resolve_compose_context() -> ComposeContext:
    """Target a running `make test-up` stack when present; else the default project.

    Cache lifetime is the process (the `lru_cache`), which for pytest equals the
    session — the active stack is treated as fixed for the run, so a mid-run stack
    change is intentionally invisible. Never raises: any docker/`.run_id` error
    falls back to the default-project context so the fixtures' own health checks
    decide skip-vs-run.
    """
    default = ComposeContext(
        project=None,
        base=["docker", "compose", "-f", _COMPOSE_FILE],
        app_service="app",
        diagnostic_services=_DIAGNOSTIC_SERVICES,
    )
    try:
        run_id = _RUN_ID_FILE.read_text().strip()
    except OSError:
        return default
    if not run_id:
        return default

    test_base = ["docker", "compose", "-f", _COMPOSE_FILE, "--profile", "test"]
    try:
        ps = subprocess.run(
            test_base + ["ps", "-q", "app-test"],
            env=_compose_env(run_id),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return default
    if ps.returncode != 0 or not ps.stdout.strip():
        return default

    return ComposeContext(
        project=run_id,
        base=test_base,
        app_service="app-test",
        diagnostic_services=("app-test", "weaviate", "ollama"),
    )


def _dump_container_diagnostics(ctx: ComposeContext, result: subprocess.CompletedProcess[str]) -> None:
    """Log exit code + recent service logs after a failed containerized CLI run.

    Best-effort: it must never raise (it runs on the failure path and must not
    mask the original assertion error). Logs are pulled from the same compose
    project/profile the CLI ran against (``ctx``), not the default project.
    """
    logger.error("Containerized CLI exited %s; dumping diagnostics.", result.returncode)
    if result.stdout:
        logger.error("CLI stdout (tail):\n%s", result.stdout[-4000:])
    if result.stderr:
        logger.error("CLI stderr (tail):\n%s", result.stderr[-4000:])
    for service in ctx.diagnostic_services:
        try:
            logs = subprocess.run(
                ctx.base + ["logs", "--tail", str(_DIAGNOSTIC_LOG_TAIL), service],
                env=_compose_env(ctx.project),
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            # Concatenate both streams: `docker compose logs` writes the log
            # stream to stdout but surfaces its own errors on stderr.
            combined = f"{logs.stdout}\n{logs.stderr}".strip()
            logger.error(
                "--- %s logs (last %d lines) ---\n%s",
                service,
                _DIAGNOSTIC_LOG_TAIL,
                combined,
            )
        except (subprocess.SubprocessError, OSError) as e:
            logger.error("Failed to collect %s logs: %s", service, e)


def _detect_environment() -> str:
    """Infer the run environment from the resolved Weaviate URL.

    E2E tests must work in both the Docker test environment (service URLs point at
    compose service hostnames) and locally (localhost). Unlike the integration
    fixture this does not consult TEST_DOCKER — that variable was eliminated; the
    service URLs set by docker-compose are the single source of truth.
    """
    weaviate_url = get_service_url("weaviate")
    if "localhost" in weaviate_url or "127.0.0.1" in weaviate_url:
        return "local"
    return "Docker"


@pytest.fixture(scope="session")
def e2e():
    """Unified e2e fixture mirroring the integration fixture's service management.

    Provides HTTP health checks and URL resolution shared with integration tests
    (via ``tests.conftest``), with environment auto-detected from service URLs so
    the same test code runs in both Docker and local environments.
    """
    config = get_integration_config()

    if not config:
        pytest.skip("Integration configuration not found in pyproject.toml")

    environment = _detect_environment()
    commands = config.get("commands", {})

    def check_service_health(service_name: str) -> bool:
        return is_service_healthy(service_name, config)

    def require_services(*services: str):
        missing = [service for service in services if not check_service_health(service)]
        if not missing:
            return

        if environment == "Docker":
            action_msg = f"Try: {commands.get('docker_start', 'make test-up')}"
        else:
            # Local mode: emit a start hint for EVERY missing service, not just the
            # first matched (avoids hiding the ollama hint when both are down).
            local_hints = {
                "weaviate": commands.get("local_weaviate_start", "start Weaviate"),
                "ollama": commands.get("local_ollama_start", "ollama serve"),
            }
            hints = [local_hints[service] for service in missing if service in local_hints]
            action_msg = "Try: " + "; ".join(hints) if hints else "Start the required services"

        health_urls: list[str] = []
        for service in missing:
            service_url = get_service_url(service)
            health_endpoint = config.get("services", {}).get(service, {}).get("health_endpoint", "")
            if service_url and health_endpoint:
                health_urls.append(f"{service_url}{health_endpoint}")
        health_check_msg = " Health check URLs: " + "; ".join(health_urls) if health_urls else ""

        pytest.skip(
            f"Required services not available: {', '.join(missing)} "
            f"(in {environment} environment). {action_msg}.{health_check_msg}"
        )

    # NOTE: unlike the integration fixture this dict intentionally omits "test_docker"
    # — TEST_DOCKER was eliminated for e2e; use "environment" ("Docker"/"local") instead.
    return {
        "config": config,
        "environment": environment,
        "check_service_health": check_service_health,
        "require_services": require_services,
        "get_service_url": lambda service: get_service_url(service),
    }


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip e2e tests that require external services when unavailable."""
    from tests.conftest import is_service_healthy

    markers_to_check = {
        "requires_weaviate": "weaviate",
        "requires_ollama": "ollama",
    }

    for item in items:
        for marker_name, service_name in markers_to_check.items():
            if item.get_closest_marker(marker_name):
                if not is_service_healthy(service_name):
                    item.add_marker(
                        pytest.mark.skip(
                            reason=(
                                f"{service_name.capitalize()} service not available. "
                                "Run docker compose or use make test-up."
                            )
                        )
                    )


# Import the test collection name constant from parent conftest
from tests.conftest import TEST_COLLECTION_NAME


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def cli_script_path(project_root):
    """Provides the absolute path to the main CLI script."""
    return project_root / "scripts" / "cli.sh"


## No per-test socket toggling required; sockets are allowed by default in non-unit suites.
@pytest.fixture(autouse=True)
def _noop_e2e_network_fixture():
    yield


@pytest.fixture(scope="session", autouse=True)
def _cleanup_testcollection_after_session():  # type: ignore[no-redef]
    """After the e2e session, delete only the 'TestCollection' in Weaviate.

    We preserve Docker volumes to avoid accidental data loss; this ensures
    ephemeral test data in 'TestCollection' doesn't persist across runs.
    """
    yield
    try:
        client = get_weaviate_client()
        try:
            if client.collections.exists(TEST_COLLECTION_NAME):
                client.collections.delete(TEST_COLLECTION_NAME)
        finally:
            try:
                close_weaviate_client()
            except Exception as e:
                import logging

                logging.warning("Failed to close Weaviate client during teardown: %s", e)
    except Exception as e:
        import logging

        logging.warning("Failed to cleanup TestCollection during teardown: %s", e)
        # Best-effort cleanup only; do not fail the test suite on cleanup issues


# <!-- external-process-test-gate-override: e2e compose fixtures drive docker compose by design -->
def _docker_available_or_skip() -> None:
    """Skip the test cleanly when the Docker daemon is unreachable."""
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not available or not running")


def _ensure_compose_service_up(service_name: str) -> None:
    """Start one compose service under the *active* project, or skip gracefully.

    Targeting the active project (a running `make test-up` stack when present) is
    what keeps this from spawning a second, conflicting default-project Weaviate.
    """
    _docker_available_or_skip()
    ctx = _resolve_compose_context()
    try:
        subprocess.run(
            ctx.base + ["up", "-d", "--wait", service_name],
            env=_compose_env(ctx.project),
            check=True,
            timeout=120,  # match `--wait-timeout 120` in scripts/dev/test-env.sh
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.skip(f"Failed to start {service_name} container: {e}")


def _app_service_running(ctx: ComposeContext) -> bool:
    """True if the resolved compose project already has a running app service."""
    try:
        ps = subprocess.run(
            ctx.base + ["ps", "-q", ctx.app_service],
            env=_compose_env(ctx.project),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return ps.returncode == 0 and bool(ps.stdout.strip())


@pytest.fixture(scope="session")
def weaviate_compose_up():  # type: ignore[no-redef]
    """Ensure a healthy Weaviate is reachable for e2e tests needing gRPC.

    Reuse-first: if Weaviate already answers its health check (e.g. a running
    `make test-up` stack), yield immediately. Otherwise start only the `weaviate`
    service under the active compose project. Volumes are preserved; teardown is
    handled by the outer harness. Skips gracefully if Docker is unavailable.
    """
    if is_service_healthy("weaviate"):
        yield
        return
    _ensure_compose_service_up("weaviate")
    yield


@pytest.fixture(scope="session")
def ollama_compose_up():  # type: ignore[no-redef]
    """Ensure a healthy Ollama is reachable for e2e tests needing a real LLM.

    Reuse-first: if Ollama already answers its health check, yield immediately;
    otherwise start only the `ollama` service under the active compose project.
    Skips gracefully if Docker is unavailable.
    """
    if is_service_healthy("ollama"):
        yield
        return
    _ensure_compose_service_up("ollama")
    yield


@pytest.fixture(scope="session")
def app_compose_up(weaviate_compose_up, ollama_compose_up):  # type: ignore[no-redef]
    """Ensure the app container is available for e2e tests needing the full stack.

    Reuse-first: if the active compose project already runs its app service (the
    `app-test` container from `make test-up`), yield immediately. Otherwise build/
    start the default-project `app` service, skipping gracefully if Docker or the
    image is unavailable.
    """
    ctx = _resolve_compose_context()
    if _app_service_running(ctx):
        yield
        return

    _docker_available_or_skip()

    # <!-- external-process-test-gate-override: e2e app fixture drives docker compose by design -->
    # The image-existence guard only applies to the default project, which builds
    # `kri-local-rag-app:latest`. The run-id test stack uses a different tag
    # (`kri-local-rag-app:test`) built by `make test-up`, so don't gate it on :latest.
    if ctx.project is None:
        image_name = "kri-local-rag-app:latest"
        try:
            subprocess.run(["docker", "image", "inspect", image_name], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pytest.skip(f"Docker image {image_name} not found. Build it first: ./scripts/docker/build_app.sh")

    try:
        subprocess.run(
            ctx.base + ["up", "-d", "--wait", ctx.app_service],
            env=_compose_env(ctx.project),
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.skip(f"Failed to start app container: {e}")

    yield


@pytest.fixture(scope="session")
def run_cli_in_container(app_compose_up):
    """Return a callable that runs ``python -m backend.qa_loop <args>`` in the app container.

    Targets whichever compose project is active — the running `make test-up` stack's
    `app-test` service when present, else the default-project `app` service — so the
    exec lands in the live stack instead of an unrelated project.
    """
    ctx = _resolve_compose_context()

    def _run_cli(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        """Run a CLI command in the app service via ``docker compose exec``.

        Args:
            args: Command-line arguments appended to ``python -m backend.qa_loop``.
            env: Optional environment variables to set inside the container.

        Returns:
            A subprocess.CompletedProcess with stdout, stderr, and returncode.
        """
        base_command = ctx.base + ["exec", "-T"]

        env_vars: list[str] = []
        if env:
            for key, value in env.items():
                env_vars.extend(["-e", f"{key}={value}"])

        full_command = base_command + env_vars + [ctx.app_service, "python", "-m", "backend.qa_loop"] + args

        result = subprocess.run(
            full_command, env=_compose_env(ctx.project), capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            _dump_container_diagnostics(ctx, result)
        return result

    return _run_cli


## Do not redefine `weaviate_client` here; use the shared fixture from tests/conftest.py
## E2E tests that need real services should depend on `weaviate_compose_up` explicitly.
