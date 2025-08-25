#!/usr/bin/env python3
"""Pytest configuration and lightweight fixtures for the E2E test suite.

Heavy docker service setup was moved to `tests/e2e/fixtures_ingestion.py` and
should be imported explicitly by tests that require real ingestion/services.
"""

import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
import weaviate


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
        # Late import to avoid side-effects during collection
        from backend.config import WEAVIATE_URL

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
            if client.collections.exists("TestCollection"):
                client.collections.delete("TestCollection")
        finally:
            try:
                client.close()
            except Exception:
                pass
    except Exception:
        # Best-effort cleanup only; do not fail the test suite on cleanup issues
        pass


@pytest.fixture(scope="session")
def weaviate_compose_up():  # type: ignore[no-redef]
    """Ensure compose Weaviate is up (no app rebuild) for e2e tests needing gRPC.

    Starts only the `weaviate` service using docker-compose. Volumes are preserved
    and the global teardown is handled by the outer harness if used.
    """
    compose_file = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")
    subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d", "--wait", "weaviate"], check=True)
    yield


@pytest.fixture(scope="session")
def ollama_compose_up():  # type: ignore[no-redef]
    """Ensure compose Ollama is up (no app rebuild) for e2e tests needing real LLM.

    Starts only the `ollama` service using docker-compose. Volumes are preserved
    and global teardown is handled elsewhere.
    """
    compose_file = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")
    subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d", "--wait", "ollama"], check=True)
    yield


@pytest.fixture(scope="session")
def app_compose_up(weaviate_compose_up, ollama_compose_up):  # type: ignore[no-redef]
    """Ensure compose app is up for e2e tests needing the full stack.

    Raises:
        pytest.UsageError: If the required Docker image is not found.
    """
    # Check if the image exists
    image_name = "kri-local-rag-app:latest"
    try:
        subprocess.run(["docker", "image", "inspect", image_name], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        raise pytest.UsageError(
            f"Docker image {image_name} not found. Please build it first, e.g., with './scripts/build_app.sh'"
        )

    compose_file = str(Path(__file__).resolve().parents[2] / "docker" / "docker-compose.yml")
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "up", "-d", "--wait", "app"],
        check=True,
    )
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
        return result

    return _run_cli


## Do not redefine `weaviate_client` here; use the shared fixture from tests/conftest.py
## E2E tests that need real services should depend on `weaviate_compose_up` explicitly.
