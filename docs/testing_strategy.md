# Testing and Mocking Strategy

This document outlines the strategy for testing and mocking in this project, focusing on creating robust, readable, and maintainable tests.

## Core Principles

1.  **Test Isolation:** Each test should run independently without interference from other tests. State leakage between tests is a common source of flakiness and should be actively prevented.
2.  **Readability:** Tests should be easy to understand. The setup, action, and assertion phases of a test should be clearly discernible.
3.  **`pytest`-Native Tooling:** We prefer using `pytest`-native features and plugins (like `pytest-mock`) over the standard `unittest.mock` library where possible, as they provide a more idiomatic and often cleaner testing experience.

## Mocking Dependencies

### The `mocker` Fixture

For most mocking scenarios, we use the `mocker` fixture from the `pytest-mock` plugin. It provides a clean, function-scoped way to patch objects and assert calls.

### The `managed_cross_encoder` Fixture

To specifically address the challenges of mocking the cross-encoder, we have created a custom fixture named `managed_cross_encoder` in `tests/unit/conftest.py`.

**Purpose:**

*   To provide a reliable, isolated mock of the `_get_cross_encoder` function for unit tests.
*   To prevent state leakage caused by the global `_cross_encoder` cache.

**Implementation:**

```python
@pytest.fixture
def managed_cross_encoder(mocker):
    """Fixture to mock _get_cross_encoder, returning a MagicMock instance."""
    mock_encoder_instance = MagicMock()
    mocker.patch(
        "backend.qa_loop._get_cross_encoder",
        return_value=mock_encoder_instance
    )
    yield mock_encoder_instance
```

**Usage:**

To use this fixture, simply add it as an argument to your test function. The fixture will automatically patch the `_get_cross_encoder` function and provide you with the `MagicMock` instance that it returns.

```python
def test_rerank_cross_encoder_success(managed_cross_encoder: MagicMock):
    """Test reranking with a successful cross-encoder prediction."""
    managed_cross_encoder.predict.return_value = [0.9, 0.1]

    # ... rest of the test
```

### State Management and Test Isolation

The `reset_cross_encoder_cache` fixture in `tests/unit/conftest.py` is an `autouse` fixture that automatically resets the `_cross_encoder` global variable to `None` before each test. This is a critical component of our strategy to prevent state leakage and ensure that each test runs in a clean environment.
