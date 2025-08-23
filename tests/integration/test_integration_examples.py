#!/usr/bin/env python3
"""Simple integration test examples demonstrating new simplified patterns."""

import pytest


@pytest.mark.requires_weaviate
def test_weaviate_integration_simple(integration):
    """Simple example of Weaviate integration test."""
    # Get service URL from integration fixture
    weaviate_url = integration["get_service_url"]("weaviate")

    # Use the URL to connect to Weaviate
    import weaviate

    hostname = weaviate_url.replace("http://", "").replace(":8080", "")

    client = weaviate.connect_to_custom(
        http_host=hostname,
        http_port=8080,
        grpc_host=hostname,
        grpc_port=50051,
        http_secure=False,
        grpc_secure=False,
    )

    try:
        assert client.is_ready()
        # Test basic operations
        collections = client.collections.list_all()
        assert collections is not None
    finally:
        client.close()


@pytest.mark.requires_ollama
def test_ollama_integration_simple(integration):
    """Simple example of Ollama integration test."""
    # Get service URL from integration fixture
    ollama_url = integration["get_service_url"]("ollama")

    # Use the URL to make API calls to Ollama
    import httpx

    response = httpx.get(f"{ollama_url}/api/version", timeout=5.0)
    assert response.status_code == 200

    version_data = response.json()
    assert "version" in version_data


@pytest.mark.requires_weaviate
@pytest.mark.requires_ollama
def test_multi_service_integration(integration):
    """Example of test requiring both Weaviate and Ollama."""
    # Both services are guaranteed to be available
    weaviate_url = integration["get_service_url"]("weaviate")
    ollama_url = integration["get_service_url"]("ollama")

    # Test both services
    import httpx
    import weaviate

    # Test Weaviate
    hostname = weaviate_url.replace("http://", "").replace(":8080", "")
    client = weaviate.connect_to_custom(
        http_host=hostname,
        http_port=8080,
        grpc_host=hostname,
        grpc_port=50051,
        http_secure=False,
        grpc_secure=False,
    )

    try:
        assert client.is_ready()
    finally:
        client.close()

    # Test Ollama
    response = httpx.get(f"{ollama_url}/api/version", timeout=5.0)
    assert response.status_code == 200


def test_with_mocking_example(monkeypatch):
    """Example of using monkeypatch for mocking external dependencies."""
    from unittest.mock import MagicMock

    # Mock an external API call
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    monkeypatch.setattr("httpx.get", lambda url, timeout: mock_response)

    # Mock a backend function
    mock_function = MagicMock(return_value="mocked result")
    monkeypatch.setattr("backend.some_module.some_function", mock_function)

    # Test code that would normally call external services
    # result = function_that_calls_external_api()
    # assert result == "expected result"


def test_environment_detection(integration):
    """Example showing how to access environment information."""
    # Check which environment we're running in
    environment = integration["environment"]  # "Docker" or "local"
    test_docker = integration["test_docker"]  # True or False

    if test_docker:
        assert environment == "Docker"
        # Services at docker service names (weaviate:8080, ollama:11434)
    else:
        assert environment == "local"
        # Services at localhost (localhost:8080, localhost:11434)

    # You can use this information to adjust test behavior
    weaviate_url = integration["get_service_url"]("weaviate")
    assert weaviate_url.startswith("http://")
    assert ":8080" in weaviate_url


def test_service_health_checking(integration):
    """Example of checking service health programmatically."""
    # Check if Weaviate is healthy
    weaviate_healthy = integration["check_service_health"]("weaviate")

    # Check if Ollama is healthy
    ollama_healthy = integration["check_service_health"]("ollama")

    # These checks are automatically done by pytest markers,
    # but you can also check manually if needed
    if weaviate_healthy:
        # weaviate_url = integration["get_service_url"]("weaviate")
        # Use Weaviate...
        pass

    if ollama_healthy:
        # ollama_url = integration["get_service_url"]("ollama")
        # Use Ollama...
        pass


@pytest.mark.requires_weaviate
def test_practical_weaviate_test(integration):
    """A more practical example of a Weaviate integration test."""
    import weaviate
    from weaviate.classes.config import DataType, Property

    weaviate_url = integration["get_service_url"]("weaviate")
    hostname = weaviate_url.replace("http://", "").replace(":8080", "")

    client = weaviate.connect_to_custom(
        http_host=hostname,
        http_port=8080,
        grpc_host=hostname,
        grpc_port=50051,
        http_secure=False,
        grpc_secure=False,
    )

    try:
        # Create a test collection
        collection_name = "ExampleCollection"

        # Clean up first
        try:
            client.collections.delete(collection_name)
        except Exception:
            pass

        # Create collection with properties
        client.collections.create(
            name=collection_name,
            properties=[
                Property(name="title", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
            ],
        )

        # Verify collection exists
        collections = client.collections.list_all()
        collection_names = [c for c in collections]
        assert collection_name.lower() in [c.lower() for c in collection_names]

        # Clean up
        client.collections.delete(collection_name)

    finally:
        client.close()
