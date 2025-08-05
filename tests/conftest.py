#!/usr/bin/env python3
"""Pytest configuration and fixtures for the test suite."""

import logging
from pathlib import Path
from urllib.parse import urlparse

import pytest
import weaviate

from backend.config import COLLECTION_NAME, WEAVIATE_URL
from backend.ingest import ingest
from backend.qa_loop import ensure_weaviate_ready_and_populated

# Configure logging for the test suite
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def docker_services_ready(docker_services):
    """
    Ensures that Docker services are ready and populated with initial data from test_data/.
    This fixture uses pytest-docker to manage the lifecycle of the services.
    It will only ingest data if the collection is empty.
    """
    logger.info("--- Verifying dependent services are ready ---")
    try:
        # This will wait for Weaviate and Ollama and handle initial data.
        ensure_weaviate_ready_and_populated()

        # Verify collection has data for the tests
        parsed = urlparse(WEAVIATE_URL)
        client = weaviate.connect_to_custom(
            http_host=parsed.hostname,
            http_port=parsed.port or 80,
            grpc_host=parsed.hostname,
            grpc_port=50051,
            http_secure=parsed.scheme == "https",
            grpc_secure=parsed.scheme == "https",
        )
        try:
            collection_exists = client.collections.exists(COLLECTION_NAME)
            has_data = False
            if collection_exists:
                collection = client.collections.get(COLLECTION_NAME)
                try:
                    next(collection.iterator())
                    has_data = True
                except StopIteration:
                    has_data = False

            if not collection_exists or not has_data:
                logger.info(f"--- Weaviate collection '{COLLECTION_NAME}' is empty. Ingesting test data. ---")
                data_dir = Path(__file__).parent.parent / "test_data"
                ingest(str(data_dir))
                logger.info("--- Test data ingested for tests. ---")
            else:
                logger.info(f"--- Weaviate collection '{COLLECTION_NAME}' already populated. Skipping ingestion. ---")

        finally:
            client.close()

        logger.info("--- All services are ready for tests. ---")

    except Exception as e:
        pytest.fail(f"Failed to verify and populate services: {e}")

    yield


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def cli_script_path(project_root):
    """Provides the absolute path to the main CLI script."""
    return project_root / "scripts" / "cli.sh"


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """
    A pytest hook to dynamically apply the docker_services_ready fixture to all tests
    that are not marked with 'nodocker'.
    """

    for item in items:
        if "docker" in item.keywords and "docker_services_ready" not in item.fixturenames:
            item.fixturenames.insert(0, "docker_services_ready")
