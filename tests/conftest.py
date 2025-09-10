#!/usr/bin/env python3
"""Root-level pytest configuration and fixtures."""

from __future__ import annotations

import logging
from pathlib import Path
import os
from typing import Any, Iterator, Optional

import pytest

# Set up a logger for this module
logger = logging.getLogger(__name__)


REPORTS_DIR = Path("reports")
LOGS_DIR = REPORTS_DIR / "logs"

# Test collection name used across fixtures to ensure consistency
TEST_COLLECTION_NAME = "TestCollection"

# Ensure CPU-friendly transformers imports during tests
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")


def pytest_sessionstart(session: pytest.Session) -> None:  # noqa: D401
    """Ensure report directories exist; preserve service URLs in local runs."""
    # In local runs, keep WEAVIATE_URL/OLLAMA_URL so tests can use running services.
    # Inside Docker, environment is managed by Compose.

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _ensure_logs_dir() -> Iterator[None]:
    # Reduce noise from third-party libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("weaviate").setLevel(logging.INFO)
    yield


# -------- Shared service health helpers (used by integration + e2e) --------


def get_integration_config() -> dict[str, Any]:
    """Read integration config from pyproject.toml (service health endpoints/timeouts)."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        return {}

    try:
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        return config.get("tool", {}).get("integration", {})
    except Exception:
        return {}


def is_http_service_available(url: str, timeout: float = 2.0) -> bool:
    """Boolean check to a health URL; returns False on any exception."""
    try:
        import requests

        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def is_service_healthy(service: str, config: Optional[dict[str, Any]] = None) -> bool:
    """Check if a named service is healthy using HTTP endpoint from pyproject config."""
    if config is None:
        config = get_integration_config()

    services = config.get("services", {})
    timeouts = config.get("timeouts", {})

    if service not in services:
        return False

    # Lazy import to avoid importing app code during unit test collection
    from backend.config import get_service_url  # local import by design

    service_url = get_service_url(service)
    health_endpoint = services[service].get("health_endpoint", "")
    health_url = f"{service_url}{health_endpoint}"
    http_timeout = timeouts.get("http_timeout", 2.0)

    return is_http_service_available(health_url, http_timeout)


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
def sample_documents_path():
    """Fixture for using the example_data directory (now only contains PDF files)."""
    return "example_data/"


@pytest.fixture
def weaviate_client():
    """Fixture for a real Weaviate client, ensuring the service is available."""
    import logging

    from backend.weaviate_client import close_weaviate_client, get_weaviate_client

    logger = logging.getLogger(__name__)
    logger.debug("Attempting to connect to Weaviate for integration tests...")

    # Use wrapper consistently - each test gets its own client instance
    client = get_weaviate_client()
    logger.debug("Successfully connected to Weaviate.")
    try:
        if client.collections.exists(TEST_COLLECTION_NAME):
            logger.debug("Deleting pre-existing test collection: %s", TEST_COLLECTION_NAME)
            client.collections.delete(TEST_COLLECTION_NAME)
    except Exception as e:
        logger.warning("Error during pre-test cleanup of collection %s: %s", TEST_COLLECTION_NAME, e)
    yield client
    try:
        # Get a fresh client for cleanup since the yielded client might be closed
        fresh_client = get_weaviate_client()
        if fresh_client.collections.exists(TEST_COLLECTION_NAME):
            logger.debug("Deleting test collection after tests: %s", TEST_COLLECTION_NAME)
            fresh_client.collections.delete(TEST_COLLECTION_NAME)
    except Exception as e:
        logger.warning("Error during post-test cleanup of collection %s: %s", TEST_COLLECTION_NAME, e)
    finally:
        close_weaviate_client()


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


# (Unit-test-only fixtures have been moved to tests/unit/conftest.py)
