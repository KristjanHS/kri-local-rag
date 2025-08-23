"""Simplified configuration for the integration test suite.

This module provides essential fixtures for integration tests with HTTP-based
health checks and unified service management using pyproject.toml configuration.
"""

import os
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest


def get_integration_config() -> dict[str, Any]:
    """Get integration configuration from pyproject.toml."""
    try:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[import-untyped]
            except ImportError:
                return {}

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        return config.get("tool", {}).get("integration", {})
    except Exception:
        return {}


def is_http_service_available(url: str, timeout: float = 2.0) -> bool:
    """Check if a service is available using HTTP health endpoint."""
    try:
        import requests

        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def get_service_url(service: str, config: Optional[dict[str, Any]] = None) -> str:
    """Get service URL based on TEST_DOCKER environment variable."""
    if config is None:
        config = get_integration_config()

    services = config.get("services", {})
    urls = config.get("urls", {})

    if service not in services:
        return ""

    test_docker = os.getenv("TEST_DOCKER", "false").lower() == "true"

    if test_docker:
        url_key = f"{service}_docker"
        return urls.get(url_key, f"http://{services[service]['host_docker']}:{services[service]['port']}")
    else:
        url_key = f"{service}_local"
        return urls.get(url_key, f"http://{services[service]['host_local']}:{services[service]['port']}")


def is_service_healthy(service: str, config: Optional[dict[str, Any]] = None) -> bool:
    """Check if a service is healthy using HTTP health endpoint."""
    if config is None:
        config = get_integration_config()

    services = config.get("services", {})
    timeouts = config.get("timeouts", {})

    if service not in services:
        return False

    service_url = get_service_url(service, config)
    health_endpoint = services[service].get("health_endpoint", "")
    health_url = f"{service_url}{health_endpoint}"
    http_timeout = timeouts.get("http_timeout", 2.0)

    return is_http_service_available(health_url, http_timeout)


@pytest.fixture(scope="session")
def integration():
    """Unified integration fixture with HTTP health checks and service management."""
    config = get_integration_config()

    if not config:
        pytest.skip("Integration configuration not found in pyproject.toml")

    test_docker = os.getenv("TEST_DOCKER", "false").lower() == "true"
    environment = "Docker" if test_docker else "local"

    def check_service_health(service_name: str) -> bool:
        return is_service_healthy(service_name, config)

    def require_services(*services: str):
        missing = []
        for service in services:
            if not check_service_health(service):
                missing.append(service)

        if missing:
            if test_docker:
                action_msg = "Try: TEST_DOCKER=true make test-up"
            else:
                if "weaviate" in missing:
                    action_msg = "Try: docker run -d -p 8080:8080 semitechnologies/weaviate:latest"
                elif "ollama" in missing:
                    action_msg = "Try: ollama serve"
                else:
                    action_msg = "Start the required services"

            health_urls = []
            for service in missing:
                service_url = get_service_url(service, config)
                health_endpoint = config.get("services", {}).get(service, {}).get("health_endpoint", "")
                if service_url and health_endpoint:
                    health_urls.append(f"{service_url}{health_endpoint}")

            health_check_msg = " Health check URLs: " + "; ".join(health_urls) if health_urls else ""

            pytest.skip(
                f"Required services not available: {', '.join(missing)} "
                f"(in {environment} environment). {action_msg}.{health_check_msg}"
            )

    return {
        "config": config,
        "environment": environment,
        "test_docker": test_docker,
        "check_service_health": check_service_health,
        "require_services": require_services,
        "get_service_url": lambda service: get_service_url(service, config),
    }


def pytest_configure(config):
    """Register pytest markers."""
    config.addinivalue_line("markers", "requires_weaviate: mark test as requiring Weaviate service")
    config.addinivalue_line("markers", "requires_ollama: mark test as requiring Ollama service")


def connect_to_weaviate_with_fallback(headers: dict[str, str] | None = None):
    """Connect to Weaviate using environment-appropriate settings."""
    import weaviate

    if not is_service_healthy("weaviate"):
        weaviate_url = get_service_url("weaviate")
        raise ConnectionError(f"Weaviate not healthy at {weaviate_url}")

    weaviate_url = get_service_url("weaviate")
    hostname = weaviate_url.replace("http://", "").replace(":8080", "")

    try:
        return weaviate.connect_to_custom(
            http_host=hostname,
            http_port=8080,
            grpc_host=hostname,
            grpc_port=50051,
            http_secure=False,
            grpc_secure=False,
            headers=headers,
        )
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Weaviate: {e}") from e


def get_ollama_url() -> str:
    """Get the appropriate Ollama URL."""
    return get_service_url("ollama")


# Mocking fixtures using monkeypatch
@pytest.fixture
def managed_embedding_model(mocker) -> MagicMock:
    """Mock backend.retriever._get_embedding_model."""
    mock_retriever = mocker.patch("backend.retriever._get_embedding_model")
    mock_model_instance = MagicMock()
    mock_model_instance.encode.return_value = [[0.1, 0.2, 0.3]]
    mock_retriever.return_value = mock_model_instance
    return mock_model_instance


@pytest.fixture
def mock_get_top_k(monkeypatch):
    """Mock get_top_k function using monkeypatch."""
    from unittest.mock import MagicMock

    mock_func = MagicMock()
    monkeypatch.setattr("backend.qa_loop.get_top_k", mock_func)
    return mock_func


@pytest.fixture
def mock_weaviate_connect(monkeypatch):
    """Mock weaviate.connect_to_custom using monkeypatch."""
    from unittest.mock import MagicMock

    mock_func = MagicMock()
    monkeypatch.setattr("weaviate.connect_to_custom", mock_func)
    return mock_func


@pytest.fixture
def mock_httpx_get(monkeypatch):
    """Mock httpx.get for Ollama client tests using monkeypatch."""
    from unittest.mock import MagicMock

    mock_func = MagicMock()
    monkeypatch.setattr("backend.ollama_client.httpx.get", mock_func)
    return mock_func
