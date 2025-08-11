"""Fixtures for real ingestion tests that require live services.

Import `docker_services_ready` from this module in tests that truly need
Weaviate/Ollama and data ingestion.
"""

import logging
from pathlib import Path
from urllib.parse import urlparse

import pytest
import weaviate

from backend.config import COLLECTION_NAME, WEAVIATE_URL
from backend.ingest import ingest
from backend.qa_loop import ensure_weaviate_ready_and_populated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def docker_services_ready(docker_services):
    """
    Ensures that Docker services are ready and populated with initial data from test_data/.
    Uses pytest-docker to manage lifecycle. Ingests only when empty.
    """
    logger.info("--- Verifying dependent services are ready ---")
    try:
        ensure_weaviate_ready_and_populated()

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
