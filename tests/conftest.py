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
    """Ensure report directories exist and unset conflicting env vars."""
    # Only unset environment variables when running outside Docker containers
    # (for host-based testing). When running inside containers, we want to
    # preserve the environment variables set by Docker Compose.
    test_docker = os.getenv("TEST_DOCKER", "false").lower() == "true"
    if not test_docker:
        os.environ.pop("WEAVIATE_URL", None)
        os.environ.pop("OLLAMA_URL", None)

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
    """Add docker environment management options."""
    docker_group = parser.getgroup("docker-env")
    docker_group.addoption(
        "--keep-docker-up",
        action="store_true",
        default=False,
        help=("Do not tear down docker compose services after tests. Equivalent to setting KEEP_DOCKER_UP=1"),
    )
    docker_group.addoption(
        "--teardown-docker",
        action="store_true",
        default=False,
        help=("Force tear down docker compose services after tests. Equivalent to setting TEARDOWN_DOCKER=1"),
    )


def pytest_configure(config: pytest.Config) -> None:  # noqa: D401
    """Minimal global configuration (no suite flags or collection hooks)."""
    return


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """No custom collection filtering; selection is by directory paths."""
    return


@pytest.fixture(scope="session")
def cross_encoder_cache_dir(project_root: Path) -> str:
    """Ensure the CrossEncoder model is available (download if needed) and return cache path."""
    from huggingface_hub import snapshot_download

    cache_dir = project_root / "model_cache"

    # Get the default model name from the config module
    from backend.config import DEFAULT_RERANKER_MODEL

    default_model_name = DEFAULT_RERANKER_MODEL

    try:
        # First, try to use cached model (no network call)
        snapshot_download(
            repo_id=default_model_name,
            cache_dir=cache_dir,
            local_files_only=True,
        )
    except Exception:
        # Model not in cache, try to download (without timeout parameter since it's not supported)
        try:
            snapshot_download(
                repo_id=default_model_name,
                cache_dir=cache_dir,
            )
        except Exception as e:
            # Skip the test if we can't download the model
            pytest.skip(
                f"Could not download CrossEncoder model '{default_model_name}' for integration test. "
                f"This test requires internet connectivity or pre-cached models. "
                f"Error: {e}"
            )

    return str(cache_dir)


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
    """
    # If running inside a Docker container, assume services are already managed
    test_docker = os.getenv("TEST_DOCKER", "false").lower() == "true"
    if test_docker:
        console.print("\n--- Running inside Docker, skipping Docker service management. ---")
        yield
        return

    project_root = Path(__file__).parent.parent
    compose_file = project_root / "docker" / "docker-compose.yml"

    # Check for Docker
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.fail("Docker is required for integration tests. Please ensure it is running.")

    console.print("\n--- Setting up Docker services for testing ---")

    with open(test_log_file, "a") as log:
        try:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "up", "-d", "--wait"],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            console.print("✓ Docker services are up and healthy.")
            log.write("✓ Docker services are up and healthy.\n")

            # --- Ensure Weaviate database is populated for tests ---
            try:
                from backend.qa_loop import ensure_weaviate_ready_and_populated

                ensure_weaviate_ready_and_populated()
                console.print("✓ Weaviate database ready for tests.")
                log.write("✓ Weaviate database ready for tests.\n")
            except Exception as e:
                console.print(f"✗ Failed to verify/populate Weaviate: {e}")
                log.write(f"✗ Failed to verify/populate Weaviate: {e}\\n")

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            stderr = e.stderr if hasattr(e, "stderr") else str(e)
            log.write("\n--- Docker Error Logs ---\n")
            log.write(str(stderr))
            pytest.fail(f"Failed to start Docker services. See logs at {test_log_file}")
        except Exception as e:
            pytest.fail(f"An unexpected error occurred during Docker setup: {e}")

    # Yield to let the tests run
    yield

    # Controlled teardown
    keep_up = request.config.getoption("--keep-docker-up") or os.getenv("KEEP_DOCKER_UP")
    if keep_up:
        console.print("\n--- Docker services left running as requested ---")
        return

    console.print("--- Tearing down Docker services (preserving volumes) ---")
    try:
        subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], check=True)
    except Exception as e:
        console.print(f"✗ Failed to tear down Docker services: {e}")


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
    """Block real Weaviate and Ollama connections for unit tests.

    Applies to any test that is located in the 'tests/unit' directory.
    """
    # Get the path of the test being run
    test_path = Path(request.node.fspath)

    # Apply the guard only if the test is inside the 'tests/unit' directory
    if "tests/unit" not in str(test_path.parent):
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
