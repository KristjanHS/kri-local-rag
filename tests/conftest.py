#!/usr/bin/env python3
"""Pytest configuration and fixtures for the test suite."""

import pytest
import subprocess
from pathlib import Path


@pytest.fixture(scope="session")
def test_log_file(tmp_path_factory):
    """Creates a unique log file for the test session."""
    log_dir = tmp_path_factory.mktemp("logs")
    log_file = log_dir / "test_run.log"
    print(f"--- Test output is being logged to: {log_file} ---")
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
    project_root = Path(__file__).parent.parent
    compose_file = project_root / "docker" / "docker-compose.yml"

    # Check for Docker
    try:
        # Add a timeout to prevent hanging if Docker daemon is unresponsive
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        # If Docker is not running, not installed, or times out, skip all Docker-dependent tests
        if isinstance(e, subprocess.TimeoutExpired):
            print("\n--- Docker daemon is unresponsive. Skipping Docker-dependent tests. ---")
        else:
            print("\n--- Docker is not running or not installed. Skipping Docker-dependent tests. ---")

        pytest.skip("Docker is not available or unresponsive, skipping Docker-dependent tests.")

    # Docker is available, manage the services
    print("\n--- Setting up Docker services for testing ---")

    with open(test_log_file, "a") as log:
        # --- Configure a file handler for the test-specific log file ---
        import logging

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
            for line in process.stdout:
                log.write(line)
                print(line, end="")  # Also print to terminal for visibility

            # Wait for the process to complete and get the return code
            process.wait(timeout=300)

            if process.returncode != 0:
                # Capture and log any remaining stderr
                stderr_output = process.stderr.read()
                log.write("\n--- Docker Error Logs ---\n")
                log.write(stderr_output)
                pytest.fail(f"Failed to start Docker services. See logs at {test_log_file}")

            print("✓ Docker services are up and healthy.")
            log.write("✓ Docker services are up and healthy.\n")

            # --- Ensure Weaviate database is populated for tests ---
            try:
                import sys

                backend_path = project_root / "backend"
                if str(backend_path) not in sys.path:
                    sys.path.insert(0, str(backend_path))
                from qa_loop import ensure_weaviate_ready_and_populated

                ensure_weaviate_ready_and_populated()

                # After the standard readiness check, ensure the collection is *not* empty for tests.
                from urllib.parse import urlparse
                import weaviate
                from config import COLLECTION_NAME, WEAVIATE_URL
                from ingest_pdf import ingest

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
                        # Ingest the bundled example data *without* deleting it afterwards
                        data_dir = project_root / "example_data"
                        ingest(str(data_dir))
                        print("✓ Example data ingested for tests.", flush=True)
                        log.write("✓ Example data ingested for tests.\n")
                    else:
                        print("✓ Weaviate collection already populated.", flush=True)
                        log.write("✓ Weaviate collection already populated.\n")
                finally:
                    client.close()

                print("✓ Weaviate database ready for tests.", flush=True)
                log.write("✓ Weaviate database ready for tests.\n")
            except Exception as e:
                print(f"✗ Failed to verify/populate Weaviate: {e}", flush=True)
                log.write(f"✗ Failed to verify/populate Weaviate: {e}\\n")

        except subprocess.TimeoutExpired:
            pytest.fail(f"Timed out waiting for Docker services. See logs at {test_log_file}")
        except Exception as e:
            pytest.fail(f"An unexpected error occurred during Docker setup: {e}")

    # Yield to let the tests run
    yield

    # Teardown is now disabled as per user instruction.
    # Containers will be left running after tests.
    print("\n--- Docker services left running for manual inspection ---")


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def cli_script_path(project_root):
    """Provides the absolute path to the main CLI script."""
    return project_root / "scripts" / "cli.sh"


# Automatically apply the docker_services fixture to all tests marked with 'docker'
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """
    A pytest hook to dynamically apply fixtures to marked tests.
    """
    if config.getoption("-m") and "not docker" in config.getoption("-m"):
        return  # Don't apply if we're explicitly skipping docker tests

    docker_marker = "docker"
    for item in items:
        if docker_marker in item.keywords:
            item.fixturenames.insert(0, "docker_services")
