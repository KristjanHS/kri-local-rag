"""Configuration for the integration test suite."""

from unittest.mock import MagicMock

import pytest


# This fixture automatically applies the 'docker_services' fixture from the root
# conftest.py to every test in the integration suite. This ensures that the
# Docker environment is up and running before any integration tests are executed.
@pytest.fixture(autouse=True)
def use_docker_services(docker_services):
    """Ensure Docker services are running for all integration tests."""
    pass


@pytest.fixture
def managed_embedding_model(mocker) -> MagicMock:
    """
    Fixture to mock backend.retriever._get_embedding_model.

    It patches the function to return a MagicMock instance, preventing real
    model loading and allowing tests to make assertions on the mock.
    """
    # Patch the function where it's defined and used in the backend
    mock_retriever = mocker.patch("backend.retriever._get_embedding_model")

    # Create a mock SentenceTransformer instance
    mock_model_instance = MagicMock()
    mock_model_instance.encode.return_value = [[0.1, 0.2, 0.3]]  # Example vector

    # Configure the patched function to return our mock model
    mock_retriever.return_value = mock_model_instance

    return mock_model_instance


@pytest.fixture
def managed_get_top_k(mocker):
    """Fixture to mock only the get_top_k function in the QA pipeline."""
    patcher = mocker.patch("backend.qa_loop.get_top_k")
    yield patcher


@pytest.fixture
def mock_weaviate_connect(mocker):
    """Fixture to mock weaviate.connect_to_custom."""
    yield mocker.patch("weaviate.connect_to_custom")


@pytest.fixture
def mock_httpx_get(mocker):
    """Fixture to mock httpx.get for Ollama client tests."""
    yield mocker.patch("backend.ollama_client.httpx.get")
