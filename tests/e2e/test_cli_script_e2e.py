"""E2E test for the CLI script."""

import logging
import os
import subprocess
import time
from unittest.mock import patch

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark the entire module as 'slow'
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module", autouse=True)
def manage_docker_compose():
    """Fixture to manage Docker Compose lifecycle for E2E tests."""
    compose_file = os.path.join(os.path.dirname(__file__), "..", "..", "docker", "docker-compose.yml")

    # Start Docker Compose
    logger.info("\n--- E2E: Starting Docker services... ---")
    start_command = ["docker", "compose", "-f", compose_file, "up", "-d", "--build"]
    subprocess.run(start_command, check=True)

    # Wait for services to be ready
    logger.info("--- E2E: Waiting for services to initialize... ---")
    time.sleep(15)  # Give time for containers to start

    # Verify that the 'app' container is running
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker/docker-compose.yml",
                "exec",
                "-T",
                "app",
                "python",
                "-c",
                "print('Container test successful')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        logger.info(f"Container check output: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        # If the check fails, get logs to help debug
        log_command = ["docker", "compose", "-f", compose_file, "logs"]
        logs = subprocess.run(log_command, capture_output=True, text=True)
        pytest.fail(
            f"E2E setup failed: 'app' container not responding. Error: {e}.\nDocker logs:\n{logs.stdout}\n{logs.stderr}"
        )

    yield  # E2E tests run here

    # Stop Docker Compose
    logger.info("\n--- E2E: Stopping Docker services... ---")
    stop_command = ["docker", "compose", "-f", compose_file, "down"]
    subprocess.run(stop_command, check=True)


@pytest.mark.e2e
def test_backend_container_imports_successfully():
    """Verify that Python imports work correctly inside the 'app' container."""
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker/docker-compose.yml",
                "exec",
                "-T",
                "app",
                "bash",
                "-c",
                (
                    "cd /app/backend && python -c 'import config; import retriever; "
                    'import ollama_client; print("Backend imports successful")\''
                ),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        assert "Backend imports successful" in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.fail(f"E2E test failed: Backend container could not import modules. Error: {e.stderr}")


@pytest.mark.e2e
@patch("os.system")
def test_cli_script_handles_no_args(mock_system):
    """Test that the CLI script runs without arguments and prints help text."""
    # Since we can't easily run the CLI from the host to the container,
    # we'll execute it directly inside the container.
    command = "cd /app && python main.py"
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "exec", "-T", "app", "bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        # Expectation: running with no args should default to showing help or a welcome message
        assert "usage: main.py [-h]" in result.stdout or "Welcome" in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.fail(f"E2E test failed: CLI script could not be executed. Error: {e.stderr}")


@pytest.mark.e2e
def test_cli_script_handles_query_command():
    """Test the 'query' command with a sample question."""
    # A simple, non-consequential question
    question = "What is the capital of France?"
    command = f"cd /app && python main.py query '{question}'"

    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "exec", "-T", "app", "bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=60,  # Allow more time for a query
            check=True,
        )
        # We expect some kind of answer, even if it's "I don't know"
        # A good check is that the output is not empty and doesn't contain error traces.
        assert len(result.stdout.strip()) > 0
        assert "Traceback" not in result.stderr
        # We can also check for some expected keywords in the answer
        assert "Answer" in result.stdout or "Sources" in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.fail(f"E2E test failed: 'query' command failed. Error: {e.stderr}")


@pytest.mark.e2e
def test_cli_script_handles_ingest_command_force_option():
    """Test the 'ingest' command with the '--force' option."""
    # This test ensures the ingest command can be triggered.
    # We use '--force' to ensure it runs even if the collection exists.
    command = "cd /app && python main.py ingest --force"

    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "exec", "-T", "app", "bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=120,  # Ingestion can be slow
            check=True,
        )
        # Check for log messages that indicate success
        assert "Starting ingestion process" in result.stdout
        assert "Finished ingestion process" in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.fail(f"E2E test failed: 'ingest --force' command failed. Error: {e.stderr}")


@pytest.mark.e2e
def test_cli_script_handles_chat_command_with_mocked_input():
    """Test the 'chat' command with a single mocked input."""
    # We'll send a single question and then 'exit'
    chat_session_commands = "echo 'What is Weaviate?' && echo 'exit'"
    command = f"cd /app && {chat_session_commands} | python main.py chat"

    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "exec", "-T", "app", "bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        # Check for the chat welcome message and the answer
        assert "Entering chat mode" in result.stdout
        # We expect some answer related to the question
        assert "database" in result.stdout.lower() or "vector" in result.stdout.lower()
        # Check for the exit message
        assert "Exiting chat mode" in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.fail(f"E2E test failed: 'chat' command failed. Error: {e.stderr}")


if __name__ == "__main__":
    pytest.main(["-s", __file__])
