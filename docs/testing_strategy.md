# Testing and Mocking Strategy

This document outlines the strategy for testing and mocking in this project, focusing on creating robust, readable, and maintainable tests.

## Core Principles

1.  **Test Isolation:** Each test should run independently without interference from other tests. State leakage between tests is a common source of flakiness and should be actively prevented.
2.  **Readability:** Tests should be easy to understand. The setup, action, and assertion phases of a test should be clearly discernible.
3.  **`pytest`-Native Tooling:** We prefer using `pytest`-native features and plugins (like `pytest-mock`) over the standard `unittest.mock` library where possible, as they provide a more idiomatic and often cleaner testing experience.

## Mocking Dependencies

### The `mocker` Fixture

For most mocking scenarios, we use the `mocker` fixture from the `pytest-mock` plugin. It provides a clean, function-scoped way to patch objects and assert calls.

## Mocking Fixtures

### The `managed_cross_encoder` Fixture

For unit tests that need to mock the cross-encoder functionality, use the `managed_cross_encoder` fixture in `tests/unit/conftest.py`.

**Purpose:**
- Provides a reliable, isolated mock of the `_get_cross_encoder` function for unit tests
- Prevents state leakage caused by the global `_cross_encoder` cache

**Usage:**
```python
def test_rerank_cross_encoder_success(managed_cross_encoder: MagicMock):
    """Test reranking with a successful cross-encoder prediction."""
    managed_cross_encoder.predict.return_value = [0.9, 0.1]
    # ... rest of the test
```

### The `mock_embedding_model` Fixture

For unit tests that need to mock the embedding model functionality, use the `mock_embedding_model` fixture.

**Usage:**
```python
def test_embedding_model_loading(self, mock_embedding_model: MagicMock):
    """Test embedding model loading and caching."""
    mock_model_instance = MagicMock()
    mock_embedding_model.return_value = mock_model_instance
    # ... rest of the test
```

### State Management and Test Isolation

The `reset_cross_encoder_cache` fixture in `tests/unit/conftest.py` is an `autouse` fixture that automatically resets the `_cross_encoder` global variable to `None` before each test. This prevents state leakage and ensures each test runs in a clean environment.
