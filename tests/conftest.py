"""Global pytest configuration for logging and per-test log capture."""

from __future__ import annotations

import logging
import os
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


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Attach a per-test file handler to the root logger."""
    nodeid_sanitized = item.nodeid.replace(os.sep, "_").replace("::", "__")
    logfile = LOGS_DIR / f"{nodeid_sanitized}.log"
    logfile.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(logfile, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Store a reference so we can remove it later
    item._log_file_handler = handler  # type: ignore[attr-defined]

    root = logging.getLogger()
    root.addHandler(handler)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Detach the per-test file handler."""
    handler: logging.Handler | None = getattr(item, "_log_file_handler", None)  # type: ignore[attr-defined]
    if handler is not None:
        root = logging.getLogger()
        root.removeHandler(handler)
        handler.close()
        delattr(item, "_log_file_handler")  # type: ignore[attr-defined]


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:  # noqa: D401
    """On failure, emit path to the per-test logfile for quick discovery."""
    if report.when == "call" and report.failed:
        try:
            nodeid_sanitized = report.nodeid.replace(os.sep, "_").replace("::", "__")
            logfile = LOGS_DIR / f"{nodeid_sanitized}.log"
            logging.getLogger(__name__).warning("Per-test log: %s", logfile)
        except Exception:
            # best-effort; don't break test reporting
            pass


#!/usr/bin/env python3
"""Root-level pytest configuration and fixtures."""

import subprocess
from pathlib import Path

import pytest
from rich.console import Console

# Set up a logger for this module
logger = logging.getLogger(__name__)
console = Console()


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
        # If Docker is not running, not installed, or times out, skip all Docker-dependent tests
        if isinstance(e, subprocess.TimeoutExpired):
            console.print("\n--- Docker daemon is unresponsive. Skipping Docker-dependent tests. ---")
        else:
            console.print("\n--- Docker is not running or not installed. Skipping Docker-dependent tests. ---")

        pytest.skip("Docker is not available or unresponsive, skipping Docker-dependent tests.")

    # Docker is available, manage the services
    console.print("\n--- Setting up Docker services for testing ---")

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
            for line in process.stdout:
                log.write(line)
                logger.info(line.strip())  # Also log to terminal for visibility

            # Wait for the process to complete and get the return code
            process.wait(timeout=300)

            if process.returncode != 0:
                # Capture and log any remaining stderr
                stderr_output = process.stderr.read()
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
                from qa_loop import ensure_weaviate_ready_and_populated

                ensure_weaviate_ready_and_populated()

                # After the standard readiness check, ensure the collection is *not* empty for tests.
                from urllib.parse import urlparse

                import weaviate
                from config import COLLECTION_NAME, WEAVIATE_URL
                from ingest import ingest

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

    # Teardown is now disabled as per user instruction.
    # Containers will be left running after tests.
    console.print("\n--- Docker services left running for manual inspection ---")


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent
