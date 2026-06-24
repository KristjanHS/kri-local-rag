"""Simplified configuration for the integration test suite.

This module provides essential fixtures for integration tests with HTTP-based
health checks and unified service management using pyproject.toml configuration.
"""

import os

import pytest

from backend.config import get_service_url
from backend.weaviate_client import (
    close_weaviate_client,
    get_weaviate_client,
)
from tests.conftest import (
    get_integration_config,
    is_service_healthy,
)


## Service health helpers are imported from tests.conftest to avoid duplication


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
                service_url = get_service_url(service)
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
        "get_service_url": lambda service: get_service_url(service),
    }


def pytest_configure(config):
    """Register pytest markers."""
    config.addinivalue_line("markers", "requires_weaviate: mark test as requiring Weaviate service")
    config.addinivalue_line("markers", "requires_ollama: mark test as requiring Ollama service")


def is_weaviate_available() -> bool:
    """Check if Weaviate service is available."""
    return is_service_healthy("weaviate")


def is_ollama_available() -> bool:
    """Check if Ollama service is available."""
    return is_service_healthy("ollama")


def pytest_collection_modifyitems(config, items):
    """Skip tests that require services that are not available."""
    for item in items:
        # Check for requires_weaviate marker
        if item.get_closest_marker("requires_weaviate"):
            if not is_weaviate_available():
                item.add_marker(
                    pytest.mark.skip(
                        reason=(
                            "Weaviate service not available. Run with 'make test-up' first or start Weaviate locally."
                        )
                    )
                )

        # Check for requires_ollama marker
        if item.get_closest_marker("requires_ollama"):
            if not is_ollama_available():
                item.add_marker(
                    pytest.mark.skip(
                        reason="Ollama service not available. Run with 'make test-up' first or start Ollama locally."
                    )
                )


def connect_to_weaviate_with_fallback(headers: dict[str, str] | None = None):
    """Connect to Weaviate using centralized wrapper with health check.

    Note: headers are currently unused by the wrapper but kept for API compatibility.
    """
    if not is_service_healthy("weaviate"):
        weaviate_url = get_service_url("weaviate")
        raise ConnectionError(f"Weaviate not healthy at {weaviate_url}")

    # Use centralized wrapper (provides caching and unified config)
    return get_weaviate_client()


@pytest.fixture(autouse=True)
def _close_weaviate_wrapper_after_each_test():
    """Ensure wrapper cache does not leak across tests."""
    # Pre-emptively clear any cached client before running the test
    close_weaviate_client()
    try:
        yield
    finally:
        # Always close and clear the cached client after the test
        close_weaviate_client()


@pytest.fixture
def weaviate_client():
    """Provide a client via the wrapper and ensure cleanup after use."""
    client = get_weaviate_client()
    try:
        yield client
    finally:
        close_weaviate_client()


def get_available_services() -> dict[str, bool]:
    """Check available services using HTTP health checks."""
    config = get_integration_config()
    services = {}

    for service in ["weaviate", "ollama"]:
        services[service] = is_service_healthy(service, config)

    return services


# Mocking fixtures using monkeypatch
@pytest.fixture
def mock_get_top_k(monkeypatch):
    """Mock get_top_k function using monkeypatch."""
    from unittest.mock import MagicMock

    mock_func = MagicMock()
    monkeypatch.setattr("backend.qa_loop.get_top_k", mock_func)
    return mock_func


@pytest.fixture
def test_collection_name():
    """Provide the test collection name.

    The weaviate_client fixture already handles collection cleanup.
    This fixture simply provides the collection name for tests that expect it.
    """
    from tests.conftest import TEST_COLLECTION_NAME

    return TEST_COLLECTION_NAME
