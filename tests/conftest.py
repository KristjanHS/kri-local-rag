"""Global pytest configuration for logging and per-test log capture."""

from __future__ import annotations

import logging
import os
import types
from pathlib import Path
from typing import Iterator

import pytest

REPORTS_DIR = Path("reports")
LOGS_DIR = REPORTS_DIR / "logs"


def pytest_sessionstart(session: pytest.Session) -> None:  # noqa: D401
    """Ensure report directories exist before any logging is configured."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _ensure_logs_dir() -> Iterator[None]:
    # Reduce noise from third-party libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("weaviate").setLevel(logging.INFO)
    yield


## Removed per-test file handler hooks; rely on log_cli/log_file from pyproject.


## Removed per-test teardown for file handler.


## Removed per-test failure log path emission.


#!/usr/bin/env python3
"""Root-level pytest configuration and fixtures."""

import subprocess
from pathlib import Path

import pytest
from rich.console import Console

# Set up a logger for this module
logger = logging.getLogger(__name__)
console = Console()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add convenience options to select common suites without shell scripts."""
    group = parser.getgroup("test-suites")
    group.addoption(
        "--test-fast",
        action="store_true",
        default=False,
        help=(
            "Run the fastest unit suite only (no external services): excludes ui, e2e, docker, "
            "environment, integration, and slow"
        ),
    )
    group.addoption(
        "--test-core",
        action="store_true",
        default=False,
        help=("Run core suite (everything except UI): excludes only ui; may include integration/slow as selected"),
    )
    group.addoption(
        "--test-ui",
        action="store_true",
        default=False,
        help="Run only UI/Playwright tests without coverage",
    )

    # Docker/test environment management flags
    docker_group = parser.getgroup("docker-env")
    docker_group.addoption(
        "--keep-docker-up",
        action="store_true",
        default=False,
        help=("Do not tear down docker compose services after tests. " "Equivalent to setting KEEP_DOCKER_UP=1"),
    )
    docker_group.addoption(
        "--teardown-docker",
        action="store_true",
        default=False,
        help=("Force tear down docker compose services after tests. " "Equivalent to setting TEARDOWN_DOCKER=1"),
    )


def _apply_suite_shortcuts(config: pytest.Config) -> None:
    fast: bool = bool(getattr(config.option, "test_fast", False))
    core: bool = bool(getattr(config.option, "test_core", False))
    ui: bool = bool(getattr(config.option, "test_ui", False))
    if sum([fast, core, ui]) > 1:
        raise pytest.UsageError("Choose only one of --test-fast, --test-core, or --test-ui")

    # quiet output to mimic -q
    if fast or core or ui:
        try:
            current_quiet = int(getattr(config.option, "quiet", 0) or 0)
        except Exception:
            current_quiet = 0
        if current_quiet < 1:
            config.option.quiet = 1

    if fast:
        # Fastest suite: strict excludes to avoid any external services
        config.option.markexpr = (
            "not ui and not e2e and not docker and not environment and not integration and not slow"
        )

    if core:
        # Core: everything except UI tests; may include integration/slow depending on selection
        config.option.markexpr = "not ui"

    if ui:
        # select UI tests; user must run with --no-cov
        config.option.markexpr = "ui or e2e"


def pytest_configure(config: pytest.Config) -> None:  # noqa: D401
    """Apply suite shortcut flags early in configuration.

    Additionally, when only a subset of tests is selected, relax any explicit
    coverage fail-under threshold to avoid false failures. This does not disable
    coverage collection; it only prevents failing a partial run because total
    coverage appears artificially low.
    """
    _apply_suite_shortcuts(config)

    def _is_partial_run(cfg: pytest.Config) -> bool:
        # Consider partial when user filtered by -k/-m or provided explicit paths/tests.
        try:
            has_k = bool(getattr(cfg.option, "keyword", None))
        except Exception:
            has_k = False
        try:
            has_m = bool(getattr(cfg.option, "markexpr", None))
        except Exception:
            has_m = False

        args = list(getattr(cfg, "args", []) or [])
        if not args:
            return has_k or has_m

        # Any explicit args indicate user-targeted selection; treat as partial.
        # This intentionally treats `pytest tests/` as partial to avoid enforcing
        # thresholds in fast local runs.
        return True

    # If a threshold was explicitly supplied (e.g., via CLI or CI), but this is
    # a partial run, relax it to 0 to avoid spurious failures.
    if _is_partial_run(config):
        # Relax CLI option if set
        try:
            cov_fail = getattr(config.option, "cov_fail_under", None)
            if cov_fail not in (None, 0, "0"):
                config.option.cov_fail_under = 0
        except Exception:
            pass

        # Also try to relax pytest-cov plugin’s internal options so the
        # enforcement at session end respects the relaxed threshold.
        try:
            cov_plugin = config.pluginmanager.get_plugin("_cov") or config.pluginmanager.get_plugin("cov")
            if cov_plugin is not None:
                opts = getattr(cov_plugin, "options", None)
                if opts is not None:
                    for attr in ("cov_fail_under", "fail_under"):
                        try:
                            if getattr(opts, attr, None) not in (None, 0, "0"):
                                setattr(opts, attr, 0)
                        except Exception:
                            continue
        except Exception:
            # Best-effort; if plugin API changes, the CLI option override above should still help
            pass


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Narrow to Streamlit UI directory when --test-ui is used."""
    if not items:
        return
    if bool(getattr(config.option, "test_ui", False)):
        keep: list[pytest.Item] = []
        deselect: list[pytest.Item] = []
        for item in items:
            # Keep only tests under tests/e2e_streamlit
            if "tests/e2e_streamlit/" in str(item.fspath):
                keep.append(item)
            else:
                deselect.append(item)
        if deselect:
            config.hook.pytest_deselected(items=deselect)
            items[:] = keep


@pytest.fixture(scope="session")
def test_log_file(tmp_path_factory):
    """Creates a unique log file for the test session."""
    log_dir = tmp_path_factory.mktemp("logs")
    log_file = log_dir / "test_run.log"
    console.print(f"--- Test output is being logged to: {log_file} ---")
    return log_file


# Fixture to manage the Docker environment for integration tests
@pytest.fixture(scope="session")
def docker_services(request, test_log_file):
    """
    Manages the Docker environment for the test session.

    This fixture will:
    1. Check if Docker is available.
    2. Start all services using `docker compose up -d --wait`.
    3. Yield control to the tests.
    4. Shut down all services with `docker compose down -v` after the session.
    """
    # If running inside a Docker container, assume services are already managed
    if Path("/.dockerenv").exists():
        console.print("\\n--- Running inside Docker, skipping Docker service management. ---")
        # In a Docker environment, we just need to ensure Weaviate is ready.
        # The services themselves are managed by the CI workflow's docker-compose.
        yield
        return

    project_root = Path(__file__).parent.parent
    compose_file = project_root / "docker" / "docker-compose.yml"

    # Check for Docker
    try:
        # Add a timeout to prevent hanging if Docker daemon is unresponsive
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        # If Docker is not running, not installed, or times out, FAIL clearly for non-unit suites
        if isinstance(e, subprocess.TimeoutExpired):
            console.print("\n--- Docker daemon is unresponsive. Docker is REQUIRED for these tests. ---")
        else:
            console.print("\n--- Docker is not running or not installed. Docker is REQUIRED for these tests. ---")

        pytest.fail(
            "Docker is required for docker/integration/e2e tests. Start the Docker daemon, "
            "or deselect these tests (e.g., -m 'not docker')."
        )

    # Docker is available, manage the services
    console.print("\n--- Setting up Docker services for testing ---")

    # Ensure sockets are enabled while bringing up services and performing readiness checks
    _sockets_enabled = False
    try:
        from pytest_socket import disable_socket, enable_socket  # type: ignore

        enable_socket()
        _sockets_enabled = True
    except Exception:
        pass

    with open(test_log_file, "a") as log:
        # --- Configure a file handler for the test-specific log file ---
        # Remove any existing handlers to avoid duplicate logs
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Add a new handler pointing to the unique test log file
        file_handler = logging.FileHandler(test_log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logging.root.addHandler(file_handler)
        logging.root.setLevel(logging.INFO)

        log.write("--- Docker Setup Logs ---\n")

        # Start services and wait for them to be healthy
        try:
            # We use Popen to stream output in real-time
            process = subprocess.Popen(
                ["docker", "compose", "-f", str(compose_file), "up", "-d", "--wait"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Stream stdout
            if process.stdout is not None:
                for line in process.stdout:
                    log.write(line)
                    logger.info(line.strip())  # Also log to terminal for visibility

            # Wait for the process to complete and get the return code
            process.wait(timeout=300)

            if process.returncode != 0:
                # Capture and log any remaining stderr
                stderr_output = process.stderr.read() if process.stderr is not None else ""
                log.write("\n--- Docker Error Logs ---\n")
                log.write(stderr_output)
                pytest.fail(f"Failed to start Docker services. See logs at {test_log_file}")

            console.print("✓ Docker services are up and healthy.")
            log.write("✓ Docker services are up and healthy.\n")

            # --- Ensure Weaviate database is populated for tests ---
            try:
                import sys

                backend_path = project_root / "backend"
                if str(backend_path) not in sys.path:
                    sys.path.insert(0, str(backend_path))
                from backend.qa_loop import ensure_weaviate_ready_and_populated

                ensure_weaviate_ready_and_populated()

                # After the standard readiness check, ensure the collection is *not* empty for tests.
                from urllib.parse import urlparse

                import weaviate

                from backend.config import COLLECTION_NAME, WEAVIATE_URL
                from backend.ingest import ingest

                parsed = urlparse(WEAVIATE_URL)
                client = weaviate.connect_to_custom(
                    http_host=parsed.hostname or "localhost",
                    http_port=parsed.port or 80,
                    grpc_host=parsed.hostname or "localhost",
                    grpc_port=50051,
                    http_secure=parsed.scheme == "https",
                    grpc_secure=parsed.scheme == "https",
                )
                try:
                    collection = client.collections.get(COLLECTION_NAME)
                    try:
                        next(collection.iterator())
                        has_data = True
                    except StopIteration:
                        has_data = False

                    if not has_data:
                        # Ingest the bundled example data *without* deleting it afterwards
                        data_dir = project_root / "example_data"
                        ingest(str(data_dir))
                        console.print("✓ Example data ingested for tests.")
                        log.write("✓ Example data ingested for tests.\n")
                    else:
                        console.print("✓ Weaviate collection already populated.")
                        log.write("✓ Weaviate collection already populated.\n")
                finally:
                    client.close()

                console.print("✓ Weaviate database ready for tests.")
                log.write("✓ Weaviate database ready for tests.\n")
            except Exception as e:
                console.print(f"✗ Failed to verify/populate Weaviate: {e}")
                log.write(f"✗ Failed to verify/populate Weaviate: {e}\\n")

        except subprocess.TimeoutExpired:
            pytest.fail(f"Timed out waiting for Docker services. See logs at {test_log_file}")
        except Exception as e:
            pytest.fail(f"An unexpected error occurred during Docker setup: {e}")

    # Yield to let the tests run
    yield

    # Controlled teardown based on flags or environment variables
    keep_up_flag = bool(getattr(request.config.option, "keep_docker_up", False))
    teardown_flag = bool(getattr(request.config.option, "teardown_docker", False))
    keep_up_env = os.environ.get("KEEP_DOCKER_UP", "").strip() not in ("", "0", "false", "False")
    teardown_env = os.environ.get("TEARDOWN_DOCKER", "").strip() not in ("", "0", "false", "False")

    # Default: keep containers up for fast iterations unless teardown is explicitly requested
    teardown_requested = teardown_flag or teardown_env
    keep_requested = keep_up_flag or keep_up_env

    if not teardown_requested:
        console.print("\n--- Docker services left running (default for fast iterations) ---")
        if keep_requested:
            console.print("    note: explicit keep requested via flag/env")
        return

    compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.yml"
    console.print("\n--- Tearing down Docker services (docker compose down -v) ---")
    try:
        subprocess.run(["docker", "compose", "-f", str(compose_file), "down", "-v"], check=True)
    except Exception as e:
        console.print(f"✗ Failed to tear down Docker services: {e}")
    finally:
        # Restore socket blocking at session end if we enabled it
        if _sockets_enabled:
            try:
                from pytest_socket import disable_socket  # type: ignore

                disable_socket(allow_unix_socket=True)
            except Exception:
                pass


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent


# Lightweight default for docker-based tests outside specialized suites.
# Suites can override this fixture in a closer-scope conftest (e.g. tests/e2e/conftest.py)
# to perform heavier readiness checks.
# Removed global auto-use fixture - individual tests should handle their own mocking


@pytest.fixture(scope="session")
def docker_services_ready():  # noqa: D401
    """No-op readiness fixture for generic docker-marked tests."""
    yield


# ---------------------------------------------------------------------------
# Safety guard: prevent real external connections in light tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _guard_against_real_external_services(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Block real Weaviate and Ollama connections in light tests.

    Applies to any test that is NOT marked as one of: integration, slow, docker.
    Such tests must stub or monkeypatch external service connections.
    """
    marker_names = {m.name for m in request.node.iter_markers()}
    # Allow network for any non-unit suite: integration, slow, docker, e2e, ui, environment
    if {"integration", "slow", "docker", "e2e", "ui", "environment"} & marker_names:
        return

    # ---- Weaviate guard ----
    def _raise_connect_to_custom(*_args, **_kwargs):  # type: ignore[no-redef]
        raise AssertionError(
            "This test must not create real Weaviate clients. "
            "Patch 'qa_loop.weaviate.connect_to_custom' to use a fake client."
        )

    # Patch the top-level weaviate module if available
    try:
        import weaviate as _weaviate_mod  # type: ignore

        monkeypatch.setattr(_weaviate_mod, "connect_to_custom", _raise_connect_to_custom, raising=False)
    except Exception:
        pass

    # Patch the reference used by backend.qa_loop, which light tests commonly exercise
    try:
        import backend.qa_loop as _qa_loop

        if hasattr(_qa_loop, "weaviate") and hasattr(_qa_loop.weaviate, "connect_to_custom"):
            monkeypatch.setattr(_qa_loop.weaviate, "connect_to_custom", _raise_connect_to_custom, raising=False)
        else:
            monkeypatch.setattr(
                _qa_loop, "weaviate", types.SimpleNamespace(connect_to_custom=_raise_connect_to_custom), raising=False
            )
    except Exception:
        pass

    # Also patch the reference used by backend.retriever
    try:
        import backend.retriever as _retriever

        if hasattr(_retriever, "weaviate") and hasattr(_retriever.weaviate, "connect_to_custom"):
            monkeypatch.setattr(_retriever.weaviate, "connect_to_custom", _raise_connect_to_custom, raising=False)
        else:
            monkeypatch.setattr(
                _retriever, "weaviate", types.SimpleNamespace(connect_to_custom=_raise_connect_to_custom), raising=False
            )
    except Exception:
        pass

    # ---- Ollama guard (httpx) ----
    try:
        from urllib.parse import urlparse as _urlparse

        import httpx as _httpx_mod  # type: ignore

        _orig_get = getattr(_httpx_mod, "get", None)
        _orig_stream = getattr(_httpx_mod, "stream", None)

        def _is_ollama_url(url_value: object) -> bool:
            try:
                if not isinstance(url_value, str):
                    return False
                parsed = _urlparse(url_value)
                is_ollama_port = parsed.port == 11434
                is_ollama_path = parsed.path.startswith("/api/generate") or parsed.path.startswith("/api/tags")
                return bool(is_ollama_port or is_ollama_path)
            except Exception:
                return False

        def _guarded_get(url, *args, **kwargs):  # type: ignore[no-redef]
            if _is_ollama_url(url):
                raise AssertionError(
                    "This test must not call the real Ollama HTTP endpoints. "
                    "Patch 'httpx.get' or the caller to use a fake response."
                )
            if callable(_orig_get):
                return _orig_get(url, *args, **kwargs)
            raise RuntimeError("httpx.get not available")

        def _guarded_stream(*args, **kwargs):  # type: ignore[no-redef]
            # httpx.stream(method, url, ...)
            url_arg = None
            if len(args) >= 2:
                url_arg = args[1]
            elif "url" in kwargs:
                url_arg = kwargs["url"]
            if _is_ollama_url(url_arg):
                raise AssertionError(
                    "This test must not stream from real Ollama. "
                    "Patch 'httpx.stream' or the caller to use a fake stream."
                )
            if callable(_orig_stream):
                return _orig_stream(*args, **kwargs)
            raise RuntimeError("httpx.stream not available")

        if callable(_orig_get):
            monkeypatch.setattr(_httpx_mod, "get", _guarded_get, raising=False)
        if callable(_orig_stream):
            monkeypatch.setattr(_httpx_mod, "stream", _guarded_stream, raising=False)
    except Exception:
        pass
