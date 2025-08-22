# Testing and Model Strategy

This document outlines the strategy for testing and model management in this project, focusing on creating robust, readable, and maintainable tests with real local models.

## Core Principles

1.  **Test Isolation:** Each test should run independently without interference from other tests. State leakage between tests is a common source of flakiness and should be actively prevented.
2.  **Real Model Testing:** Integration tests should use real local models to validate actual behavior, performance, and component interactions. Mocking is reserved for external services, databases, and other non-model components.
3.  **Readability:** Tests should be easy to understand. The setup, action, and assertion phases of a test should be clearly discernible.
4.  **`pytest`-Native Tooling:** We prefer using `pytest`-native features and plugins (like `pytest-mock`) over the standard `unittest.mock` library where possible, as they provide a more idiomatic and often cleaner testing experience.

## Mocking Strategy: Pytest Fixtures

The **target approach** for all tests (both unit and integration) is to use `pytest` fixtures to manage mocks. Fixtures provide clean dependency injection into tests, are managed by the test runner, and prevent the state leakage issues that can arise from using decorators like `@patch`.

### Integration Test Strategy

Integration tests verify the interaction between different components of the application. We use real local models for ML components while mocking external services, databases, and network calls that are not the focus of the test.

#### Real Local Models in Integration Tests

Integration tests should use real local models to ensure:
- Actual model behavior is validated
- Component interactions work with real ML models
- Model-specific issues are caught early
- Performance characteristics are tested

**Local Model Management:**
- Models are cached locally to avoid repeated downloads
- Cache directories are configured per test session
- Models are loaded once and reused across tests
- Environment variables control model paths and versions

**Usage in an Integration Test:**
```python
def test_retrieval_with_real_models(mock_weaviate_connect, real_embedding_model):
    """Integration test for retriever using real local embedding model."""
    from backend.retriever import get_top_k

    # real_embedding_model fixture provides actual SentenceTransformer model
    # (cached locally, no network downloads)

    # Setup Weaviate mock for external service
    mock_client = MagicMock()
    mock_weaviate_connect.return_value = mock_client

    # Test the integration with real model
    result = get_top_k("test question", k=5)

    # Verify the flow with actual model behavior
    assert len(result) <= 5  # Real model produces actual results
    # ... other assertions based on real model output ...
```

### Key Mocking Fixtures

Our `conftest.py` files provide several reusable fixtures for common mocking scenarios. These focus on external services, databases, and network calls - NOT models.

#### `mock_weaviate_connect`

This fixture mocks the Weaviate connection for integration tests that need to test retrieval logic without requiring a real Weaviate instance.

**Purpose:**
- Prevents network calls to external vector databases
- Allows testing of retrieval logic with controlled mock responses
- Maintains test isolation from external services

**Usage:**
```python
def test_retrieval_with_mock_db(mock_weaviate_connect, real_embedding_model):
    """Test retrieval pipeline with real model but mocked database."""
    from backend.retriever import get_top_k

    # Mock Weaviate client
    mock_client = MagicMock()
    mock_client.query.return_value = {"data": {"Get": {"Document": []}}}
    mock_weaviate_connect.return_value = mock_client

    # Test with real model, mocked external service
    result = get_top_k("test question", k=5)

    # Verify real model was used but external service was mocked
    mock_weaviate_connect.assert_called_once()
    # ... other assertions ...
```

#### `mock_httpx_get`

This fixture mocks HTTP requests for testing API integrations without actual network calls.

**Purpose:**
- Prevents external API calls during testing
- Allows controlled responses for different test scenarios
- Speeds up tests by eliminating network latency

**Usage:**
```python
def test_api_integration_with_mock(mock_httpx_get, real_embedding_model):
    """Test API integration with real model processing but mocked HTTP calls."""
    # Configure mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "success"}
    mock_httpx_get.return_value = mock_response

    # Test integration with real model, mocked network
    result = process_with_api("test input")

    # Verify both real model usage and mocked network calls
    mock_httpx_get.assert_called_once()
    # ... other assertions ...
```

### Local Model Testing

The project uses real local models in integration tests to ensure accurate validation of ML components.

#### Real Local Model Fixtures (Recommended)
```python
def test_model_integration(real_embedding_model, real_reranker_model):
    """Test model integration using real local models."""
    from backend.retriever import get_top_k

    # Fixtures provide actual cached models (no network downloads)
    assert real_embedding_model is not None
    assert real_reranker_model is not None

    # Test actual model behavior
    query = "What is machine learning?"
    embedding = real_embedding_model.encode(query)
    assert embedding.shape == (384,)  # Real dimensionality check

    # Test reranking with real models
    docs = ["ML is AI.", "Weather is nice."]
    scores = real_reranker_model.predict([[query, docs[0]], [query, docs[1]]])
    assert len(scores) == 2
    assert scores[0] > scores[1]  # ML doc should score higher
```

#### Model Configuration Testing
```python
def test_model_configuration_with_env(monkeypatch):
    """Test environment variable overrides for model configuration."""
    from backend import config

    monkeypatch.setenv("EMBED_REPO", "custom/sentence-transformer")
    monkeypatch.setenv("EMBED_COMMIT", "abc123")

    # Reload config to pick up environment changes
    import importlib
    importlib.reload(config)

    assert config.EMBEDDING_MODEL == "custom/sentence-transformer"
    assert config.EMBED_COMMIT == "abc123"
```

#### Model Cache Management
```python
import time

def test_model_caching_behavior(real_embedding_model, reset_global_cache):
    """Test that models are properly cached across test runs."""
    from backend.models import _embedding_model

    # First access loads model
    model1 = real_embedding_model
    first_load_time = time.time()

    # Second access should return cached model
    model2 = real_embedding_model
    second_load_time = time.time()

    # Same instance should be returned
    assert model1 is model2
    assert model1 is _embedding_model

    # Second access should be faster
    assert second_load_time - first_load_time < 1.0
```

### General Purpose Mocking

For scenarios not covered by the specific fixtures above, use the `mocker` fixture from `pytest-mock` directly in your test.

```python
def test_general_mocking(mocker):
    # Patch a function within the scope of this test
    mock_obj = mocker.patch("path.to.some.function", return_value="mocked")

    # ... test implementation

    mock_obj.assert_called_once()
```

### Local Model Management and Caching

The project uses sophisticated caching strategies for real local models to ensure efficient testing:

#### Model Cache Architecture
- **`backend.models`**: Primary cache for `_embedding_model` and `_cross_encoder`
- **Session-scoped caching**: Models loaded once per test session and reused
- **Environment-based paths**: `HF_HOME` and `SENTENCE_TRANSFORMERS_HOME` control cache locations
- **Automatic cleanup**: Cache directories cleaned up after test sessions

#### Real Model Fixtures
- **`real_embedding_model`**: Provides actual SentenceTransformer model with caching
- **`real_reranker_model`**: Provides actual CrossEncoder model with caching
- **`reset_global_cache`**: Resets model caches between tests to prevent state leakage
- **Automatic cache management**: Fixtures handle model loading and cleanup automatically

#### Cache Management Best Practices
```python
def test_with_proper_cache_management(real_embedding_model, reset_global_cache):
    """Test with proper cache management for real models."""
    from backend.models import _embedding_model

    # Fixture ensures model is loaded and cached
    assert _embedding_model is real_embedding_model

    # Test operations with real model
    embedding = real_embedding_model.encode("test")
    assert embedding.shape == (384,)

    # reset_global_cache fixture ensures clean state for next test
```

#### Performance Optimization
- **Lazy loading**: Models loaded only when first requested
- **Memory management**: Models kept in memory across tests within session
- **Disk caching**: Downloaded models cached to disk to avoid repeated downloads
- **Timeout handling**: Model loading operations have reasonable timeouts

## Testing Strategy Guidelines

### When to Use Real Models vs Mocks

| Component Type | Recommended Approach | Reasoning |
|---|---|---|---|
| **ML Models** (SentenceTransformer, CrossEncoder) | **Real Local Models** | Need to validate actual model behavior, performance, and component interactions |
| **External Services** (Weaviate, Ollama) | **Mock** | Network calls slow tests, external dependencies unreliable |
| **Database Operations** | **Mock** | Test data isolation, avoid external dependencies |
| **File I/O Operations** | **Mock** | Filesystem operations can be slow and unreliable |
| **Network APIs** | **Mock** | External API calls introduce latency and unreliability |
| **Configuration Systems** | **Real** | Need to test actual config loading and environment variables |

### Best Practices for Real Model Testing

1. **Cache Management**: Always use fixtures that handle model caching properly
2. **Timeout Handling**: Set reasonable timeouts for model loading operations
3. **Performance Expectations**: Real models are slower than mocks - account for this in test design
4. **Resource Management**: Ensure models are properly cleaned up between tests
5. **Offline Support**: Tests should work in environments without internet connectivity

## Compose-Only Testing Approach

For integration tests requiring real external services (Weaviate, Ollama) alongside real local models, we use Docker Compose to provide a consistent, isolated test environment.

### Quick Start

```bash
# Start test environment (smart rebuild detection)
make test-up

# Run tests in container
docker compose -f docker/docker-compose.yml -f docker/compose.test.yml -p "$(cat .run_id)" exec -T app /opt/venv/bin/python -m pytest tests/integration/

# Stop environment
make test-down
```

**Important**: Use `/opt/venv/bin/python` (not `.venv/bin/python`) in the container.

### Key Features

- **Smart rebuilds**: Only rebuilds when dependencies change (`requirements.txt`, `pyproject.toml`, Dockerfiles)
- **Live code mounting**: Application and test code mounted as volumes for instant updates
- **Service isolation**: Unique project names prevent conflicts between test runs
- **Mixed testing**: Real local models + mocked external services where appropriate
- **Internal networking**: Services available at `http://weaviate:8080` and `http://ollama:11434`

### Writing Tests with Real Models

Tests should use real local models while mocking external services:

```python
from pathlib import Path
from unittest.mock import MagicMock
import pytest

def test_with_real_models_mock_services(mock_weaviate_connect, real_embedding_model):
    """Integration test using real local models with mocked external services."""
    if not Path("/.dockerenv").exists():
        pytest.skip("This test requires the Compose test environment. Run with 'make test-up' first.")

    # Use real local model for actual ML processing
    query = "What is machine learning?"
    embedding = real_embedding_model.encode(query)
    assert embedding.shape == (384,)

    # Mock external vector database
    mock_client = MagicMock()
    mock_weaviate_connect.return_value = mock_client

    # Test the integration with real model + mocked service
    result = process_query_with_vector_search(query)

    # Verify both real model usage and mocked service calls
    mock_weaviate_connect.assert_called_once()
    assert isinstance(result, list)  # Real model produces actual results
```

### Debugging

```bash
make test-logs  # View service logs
make test-clean # Clean build cache
```
