# Testing and Mocking Strategy

This document outlines the strategy for testing and mocking in this project, focusing on creating robust, readable, and maintainable tests.

## Core Principles

1.  **Test Isolation:** Each test should run independently without interference from other tests. State leakage between tests is a common source of flakiness and should be actively prevented.
2.  **Readability:** Tests should be easy to understand. The setup, action, and assertion phases of a test should be clearly discernible.
3.  **`pytest`-Native Tooling:** We prefer using `pytest`-native features and plugins (like `pytest-mock`) over the standard `unittest.mock` library where possible, as they provide a more idiomatic and often cleaner testing experience.

## Mocking Strategy

### Target Approach: Modern Pytest Fixtures (Recommended)

**For new unit tests, use the modern pytest-native fixture approach:**

#### The `managed_cross_encoder` Fixture

This is the **target approach** for mocking cross-encoder functionality in unit tests. Use the `managed_cross_encoder` fixture in `tests/unit/conftest.py`.

**Purpose:**
- Provides a reliable, isolated mock of the `_get_cross_encoder` function for unit tests
- Prevents state leakage caused by the global `_cross_encoder` cache
- Uses pytest-native `mocker` fixture for clean, function-scoped patching

**Usage:**
```python
def test_rerank_cross_encoder_success(managed_cross_encoder: MagicMock):
    """Test reranking with a successful cross-encoder prediction."""
    managed_cross_encoder.predict.return_value = [0.9, 0.1]
    # ... rest of the test
```

#### The `mock_embedding_model` Fixture

This is the **target approach** for mocking embedding model functionality in unit tests.

**Usage:**
```python
def test_embedding_model_loading(self, mock_embedding_model: MagicMock):
    """Test embedding model loading and caching."""
    mock_model_instance = MagicMock()
    mock_embedding_model.return_value = mock_model_instance
    # ... rest of the test
```

### Current AS-IS Approaches (Legacy)

**These approaches are currently used in existing tests but are NOT the target for new development:**

#### Integration Tests: `@patch` Decorators

Integration tests in `tests/integration/` still use `unittest.mock.patch` decorators. This is acceptable for integration tests where the scope is broader, but unit tests should prefer the fixture approach.

```python
@patch("backend.qa_loop.generate_response")
@patch("backend.qa_loop.get_top_k")
def test_integration_scenario(mock_get_top_k, mock_generate_response):
    # ... test implementation
```

#### The `mocker` Fixture (General Purpose)

For general mocking scenarios not covered by specific fixtures, the `mocker` fixture from `pytest-mock` is available:

```python
def test_general_mocking(mocker):
    mock_obj = mocker.patch("module.function", return_value="mocked")
    # ... test implementation
```

### State Management and Test Isolation

The `reset_cross_encoder_cache` fixture in `tests/unit/conftest.py` is an `autouse` fixture that automatically resets the `_cross_encoder` global variable to `None` before each test. This prevents state leakage and ensures each test runs in a clean environment.
