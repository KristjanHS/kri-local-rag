#!/usr/bin/env python3
"""Pytest configuration and fixtures for the test suite."""

import logging
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_log_file(tmp_path_factory):
    """Creates a unique log file for the test session."""
    log_dir = tmp_path_factory.mktemp("logs")
    log_file = log_dir / "test_run.log"
    print(f"--- Test output is being logged to: {log_file} ---")

    # --- Configure a file handler for the test-specific log file ---
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logging.root.addHandler(file_handler)
    logging.root.setLevel(logging.INFO)

    return log_file


@pytest.fixture(scope="session")
def services_ready(test_log_file):
    """
    Checks if dependent services are ready and populated.
    This fixture assumes that Docker services are already running.
    """
    project_root = Path(__file__).parent.parent
    print("\n--- Verifying dependent services are ready ---")

    with open(test_log_file, "a") as log:
        log.write("--- Service Readiness Check ---\n")
        try:
            # --- Ensure Weaviate database is populated for tests ---
            from urllib.parse import urlparse

            import weaviate

            from backend.config import COLLECTION_NAME, WEAVIATE_URL
            from backend.ingest import ingest
            from backend.qa_loop import ensure_weaviate_ready_and_populated

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
                collection = client.collections.get(COLLECTION_NAME)
                try:
                    next(collection.iterator())
                    has_data = True
                except StopIteration:
                    has_data = False

                if not has_data:
                    data_dir = project_root / "example_data"
                    ingest(str(data_dir))
                    print("✓ Example data ingested for tests.", flush=True)
                    log.write("✓ Example data ingested for tests.\n")
                else:
                    print("✓ Weaviate collection already populated.", flush=True)
                    log.write("✓ Weaviate collection already populated.\n")
            finally:
                client.close()

            print("✓ All services are ready for tests.", flush=True)
            log.write("✓ All services are ready for tests.\n")

        except Exception as e:
            pytest.fail(f"Failed to verify and populate services: {e}\n. See logs at {test_log_file}")

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
    A pytest hook to dynamically apply the services_ready fixture to all tests.
    """
    # Apply the fixture to all tests, as they are integration tests.
    for item in items:
        if "services_ready" not in item.fixturenames:
            item.fixturenames.insert(0, "services_ready")
