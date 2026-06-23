#!/usr/bin/env python3
"""E2E test configuration and fixtures."""

import logging
import subprocess
from pathlib import Path

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


def _dump_container_diagnostics(compose_file: str, result: subprocess.CompletedProcess[str]) -> None:
    """Log exit code + recent service logs after a failed containerized CLI run.

    Best-effort: it must never raise (it runs on the failure path and must not
    mask the original assertion error).
    """
    logger.error("Containerized CLI exited %s; dumping diagnostics.", result.returncode)
    if result.stdout:
        logger.error("CLI stdout (tail):\n%s", result.stdout[-4000:])
    if result.stderr:
        logger.error("CLI stderr (tail):\n%s", result.stderr[-4000:])
    for service in _DIAGNOSTIC_SERVICES:
        try:
            logs = subprocess.run(
                ["docker", "compose", "-f", compose_file, "logs", "--tail", str(_DIAGNOSTIC_LOG_TAIL), service],
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


@pytest.fixture(scope="session")
def weaviate_compose_up():  # type: ignore[no-redef]
    """Ensure compose Weaviate is up (no app rebuild) for e2e tests needing gRPC.

    Starts only the `weaviate` service using docker-compose. Volumes are preserved
    and the global teardown is handled by the outer harness if used.
    Skips tests gracefully if Docker is not available.
    """
    # Check if Docker is available
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not available or not running")

    compose_file = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")
    try:
        subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d", "--wait", "weaviate"], check=True)
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start Weaviate container: {e}")
    yield


@pytest.fixture(scope="session")
def ollama_compose_up():  # type: ignore[no-redef]
    """Ensure compose Ollama is up (no app rebuild) for e2e tests needing real LLM.

    Starts only the `ollama` service using docker-compose. Volumes are preserved
    and global teardown is handled elsewhere.
    Skips tests gracefully if Docker is not available.
    """
    # Check if Docker is available
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not available or not running")

    compose_file = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")
    try:
        subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d", "--wait", "ollama"], check=True)
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start Ollama container: {e}")
    yield


@pytest.fixture(scope="session")
def app_compose_up(weaviate_compose_up, ollama_compose_up):  # type: ignore[no-redef]
    """Ensure compose app is up for e2e tests needing the full stack.

    Skips tests gracefully if Docker or the required image is not available.
    """
    # Check if Docker is available
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not available or not running")

    # Check if the image exists
    image_name = "kri-local-rag-app:latest"
    try:
        subprocess.run(["docker", "image", "inspect", image_name], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        pytest.skip(
            f"Docker image {image_name} not found. Please build it first, e.g., with './scripts/docker/build_app.sh'"
        )

    compose_file = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")
    try:
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "up", "-d", "--wait", "app"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start app container: {e}")

    yield


@pytest.fixture(scope="session")
def run_cli_in_container(app_compose_up):
    """
    Returns a callable that executes a command in the 'app' docker-compose service.
    Uses the existing app container which can run both Streamlit and CLI commands.
    """
    compose_file = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")

    def _run_cli(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        """
        Runs a command in the 'app' service using docker compose exec.
        This leverages the existing app container that can run CLI commands.

        Args:
            args: Command-line arguments to pass to the python command.
            env: Optional dictionary of environment variables to set in the container.

        Returns:
            A subprocess.CompletedProcess instance with stdout, stderr, and returncode.
        """
        # Use docker compose exec to run commands in the existing app container
        base_command = ["docker", "compose", "-f", compose_file, "exec", "-T"]

        env_vars = []
        if env:
            for key, value in env.items():
                env_vars.extend(["-e", f"{key}={value}"])

        # The command to run in the app container
        full_command = base_command + env_vars + ["app", "python", "-m", "backend.qa_loop"] + args

        result = subprocess.run(full_command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _dump_container_diagnostics(compose_file, result)
        return result

    return _run_cli


## Do not redefine `weaviate_client` here; use the shared fixture from tests/conftest.py
## E2E tests that need real services should depend on `weaviate_compose_up` explicitly.
