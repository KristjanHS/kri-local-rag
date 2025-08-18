# Testing and Mocking Strategy

This document outlines the strategy for testing and mocking in this project, focusing on creating robust, readable, and maintainable tests.

## Core Principles

1.  **Test Isolation:** Each test should run independently without interference from other tests. State leakage between tests is a common source of flakiness and should be actively prevented.
2.  **Readability:** Tests should be easy to understand. The setup, action, and assertion phases of a test should be clearly discernible.
3.  **`pytest`-Native Tooling:** We prefer using `pytest`-native features and plugins (like `pytest-mock`) over the standard `unittest.mock` library where possible, as they provide a more idiomatic and often cleaner testing experience.

## Mocking Strategy: Pytest Fixtures

The **target approach** for all tests (both unit and integration) is to use `pytest` fixtures to manage mocks. Fixtures provide clean dependency injection into tests, are managed by the test runner, and prevent the state leakage issues that can arise from using decorators like `@patch`.

### Integration Test Mocking

Integration tests verify the interaction between different components of the application. We use fixtures to mock external services or heavy components that are not the focus of the test.

#### `managed_embedding_model`

This fixture patches the embedding model getter in the `retriever` module. This is crucial for integration tests that need to verify the retrieval pipeline without loading the actual, resource-intensive `SentenceTransformer` model.

**Purpose:**
- Prevents the real embedding model from being loaded during integration tests.
- Allows tests to simulate the behavior of the embedding model, such as the vectors it returns, while testing the interaction with other components like the Weaviate client.

**Usage in an Integration Test:**
```python
def test_retrieval_with_local_vectorization(mock_weaviate_connect, managed_embedding_model):
    """Integration test for retriever ensuring it uses the local embedding model."""
    from backend.retriever import get_top_k

    # Setup embedding model mock behavior via the fixture
    mock_array = MagicMock()
    mock_array.tolist.return_value = [0.1, 0.2, 0.3]
    managed_embedding_model.encode.return_value = mock_array

    # Setup Weaviate mock (as this is an integration test, we might mock the client)
    mock_client = MagicMock()
    # ... configure mock_client ...
    mock_weaviate_connect.return_value = mock_client

    # Test the integration
    result = get_top_k("test question", k=5)

    # Verify the flow
    managed_embedding_model.encode.assert_called_once_with("test question")
    # ... other assertions ...
```

### Key Mocking Fixtures

Our `conftest.py` files provide several reusable fixtures for common mocking scenarios.

#### `managed_qa_functions` (for QA Pipeline Tests)

This fixture provides a dictionary of mocks for the core functions in the question-answering pipeline.

**Purpose:**
- Mocks `get_top_k` and `generate_response` in `backend.qa_loop`.
- Allows tests to control the inputs and outputs of the QA pipeline without hitting real services.
- Uses the `mocker` fixture internally to ensure patches are scoped correctly to the test function.

**Usage:**
```python
def test_qa_pipeline_produces_answer(managed_qa_functions):
    """Ensure `answer()` returns a meaningful response."""
    # Configure the mocks provided by the fixture
    managed_qa_functions["get_top_k"].return_value = ["Some context."]
    managed_qa_functions["generate_response"].return_value = ("An answer.", None)

    result = answer("A question?")

    assert result == "An answer."
    managed_qa_functions["get_top_k"].assert_called_once()
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

### State Management and Caching

Some modules, like `qa_loop`, use a global cache for heavy objects (e.g., `_cross_encoder`). To prevent state from leaking between tests, an `autouse` fixture automatically resets this cache before each test run, ensuring a clean state.
