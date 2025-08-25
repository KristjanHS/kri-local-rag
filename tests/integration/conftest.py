"""Simplified configuration for the integration test suite.

This module provides essential fixtures for integration tests with HTTP-based
health checks and unified service management using pyproject.toml configuration.
"""

import os
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from backend.config import get_service_url


def get_integration_config() -> dict[str, Any]:
    """Get integration configuration from pyproject.toml."""
    try:
        import tomllib
    except ImportError:
        return {}  # No TOML support available

    try:
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


def is_service_healthy(service: str, config: Optional[dict[str, Any]] = None) -> bool:
    """Check if a service is healthy using HTTP health endpoint."""
    if config is None:
        config = get_integration_config()

    services = config.get("services", {})
    timeouts = config.get("timeouts", {})

    if service not in services:
        return False

    service_url = get_service_url(service)
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


def get_available_services() -> dict[str, bool]:
    """Check available services using HTTP health checks."""
    config = get_integration_config()
    services = {}

    for service in ["weaviate", "ollama"]:
        services[service] = is_service_healthy(service, config)

    return services


# Model cache and integration fixtures
@pytest.fixture(scope="session")
def integration_model_cache(tmp_path_factory):
    """Create a session-level model cache for integration tests."""
    cache_dir = tmp_path_factory.mktemp("integration_model_cache")
    return str(cache_dir)


@pytest.fixture
def real_model_loader():
    """Fixture for loading real models in integration tests."""
    from backend.models import load_embedder, load_reranker

    return {
        "embedder": load_embedder,
        "reranker": load_reranker,
    }


@pytest.fixture(scope="session")
def real_embedding_model():
    """Session-scoped embedding model; skips tests if unavailable."""
    import logging

    from backend.models import load_embedder

    logger = logging.getLogger(__name__)
    try:
        model = load_embedder()
    except Exception as e:
        logger.info("Skipping tests requiring embedding model: %s", e)
        pytest.skip(f"Embedding model unavailable: {e}")
    # Quick smoke check to ensure the model is usable
    try:
        _ = model.encode("ok")  # type: ignore[attr-defined]
    except Exception as e:
        logger.info("Skipping tests due to embedding model health check failure: %s", e)
        pytest.skip(f"Embedding model health check failed: {e}")
    return model


@pytest.fixture(scope="session")
def real_reranker_model():
    """Session-scoped reranker model; skips tests if unavailable."""
    import logging

    from backend.models import load_reranker

    logger = logging.getLogger(__name__)
    try:
        model = load_reranker()
    except Exception as e:
        logger.info("Skipping tests requiring reranker model: %s", e)
        pytest.skip(f"Reranker model unavailable: {e}")
    # Quick smoke check to ensure the model is usable
    try:
        _ = model.predict([["q", "d"]])  # type: ignore[attr-defined]
    except Exception as e:
        logger.info("Skipping tests due to reranker model health check failure: %s", e)
        pytest.skip(f"Reranker model health check failed: {e}")
    return model


@pytest.fixture
def model_health_checker():
    """Fixture for checking model health."""

    def check_model_health(model, test_sentence="Test sentence"):
        try:
            if hasattr(model, "encode"):
                # Embedding model
                embedding = model.encode(test_sentence)
                return embedding is not None and len(embedding) > 0
            elif hasattr(model, "predict"):
                # Cross-encoder model
                scores = model.predict([(test_sentence, test_sentence)])
                return scores is not None and len(scores) > 0
            else:
                return False
        except Exception:
            return False

    def get_model_info(model, model_type):
        """Get model information."""
        try:
            if hasattr(model, "encode"):
                # Embedding model
                embedding = model.encode("Test")
                return {"healthy": True, "embedding_dim": len(embedding), "model_type": "embedding"}
            elif hasattr(model, "predict"):
                # Cross-encoder model
                model.predict([("Test", "Test")])  # Test the model
                return {"healthy": True, "model_type": "cross_encoder"}
            else:
                return {"healthy": False, "model_type": "unknown"}
        except Exception:
            return {"healthy": False, "model_type": model_type}

    return {"check_health": check_model_health, "get_info": get_model_info}


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
