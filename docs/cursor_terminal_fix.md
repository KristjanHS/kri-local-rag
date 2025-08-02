# A Developer's Guide to Debugging Hanging Tests in Cursor

This document provides a comprehensive guide to diagnosing and fixing a complex issue where `pytest` hangs during test execution in the Cursor IDE, particularly on Linux/WSL environments. The core problem was ultimately traced to `pytest`'s test collection phase hanging due to heavy imports, but the debugging process uncovered several best practices for creating a more robust and stable testing environment.

## 1. The Symptoms: A Silent Hang

The primary symptom was that running `pytest` in the integrated terminal would result in a silent, indefinite hang.
- No test output was displayed.
- Even `print` statements at the start of test files were not visible.
- Manually stopping the command (`Ctrl+C`) would also hang for several minutes before terminating.
- Log files intended to capture output were never created.

These symptoms pointed to a problem occurring at the earliest stages of test execution, before fixtures were set up or tests were run.

## 2. The Root Cause: Test Collection and Heavy Imports

The investigation revealed that the hang was happening during `pytest`'s **test collection phase**.

-   **What is Test Collection?** Before running any tests, `pytest` scans the specified directories to find all files and functions that are tests. To do this, it must **import** each test file.
-   **The Culprit:** One or more of the test files (`tests/test_...`) contained a top-level `import` statement for a heavy machine learning library (`sentence_transformers`). When `pytest` tried to import this file during collection, the library would begin a long-running process (like downloading models or initializing a GPU), causing the entire `pytest` process to hang before it could report any progress.

## 3. The Solution: Isolate and Defer Heavy Imports

The definitive solution was to **move the heavy imports from the top of the test files into the specific functions that actually use them**. This ensures that the expensive import operation only happens when a test is *run*, not during the fast collection phase.

**Original Code (in `tests/test_hybrid_search_fix.py`):**
```python
# This top-level import hangs pytest during collection
from retriever import get_top_k, _get_embedding_model

class TestHybridSearchFix:
    def test_embedding_model_loading(self):
        # ...
```

**Fixed Code:**
```python
# Note at the top of the file explains the change
# Note: The main 'from retriever import ...' is moved inside the test functions
# to prevent hanging during pytest collection.

class TestHybridSearchFix:
    def test_embedding_model_loading(self):
        # Import is moved inside the function that needs it
        from retriever import _get_embedding_model
        # ...
```

This simple refactoring was the ultimate fix for the hanging issue.

## 4. Additional Best Practices Uncovered

During the debugging process, we implemented several other improvements that are highly recommended for a robust test suite.

### 4.1. Making Tests Visible: Disable Output Capturing

When the terminal was not showing output, the key to getting visibility was to disable `pytest`'s built-in output capturing. This forces all `print` statements and subprocess output to be streamed directly to the terminal in real-time.

**Command:**
```bash
# The -s and --capture=no flags are crucial for real-time output
pytest -v -s --capture=no
```

### 4.2. Separating Unit and Integration Tests with Markers

To prevent slow, I/O-bound tests from running during routine checks, we introduced custom `pytest` markers.

1.  **Register the markers in `pytest.ini`:**
    ```ini
    [pytest]
    markers =
        slow: marks tests as slow (e.g., model downloads)
        docker: tests that require running Docker services
    ```

2.  **Mark the tests in the code:**
    ```python
    # In tests/test_cli_script_integration.py
    import pytest
    pytestmark = pytest.mark.docker

    # In tests/test_startup_performance.py
    @pytest.mark.slow
    def test_heavy_imports_eventually_succeed(self):
        # ...
    ```

3.  **Run only the fast tests:**
    ```bash
    # This command skips any test marked with 'docker' or 'slow'
    pytest -m "not docker and not slow"
    ```

### 4.3. Automating Docker Setup and Teardown with Fixtures

To make the Docker-dependent integration tests reliable and self-contained, we created a central fixture in `tests/conftest.py`.

**Key Features of the Fixture:**
-   **Session-Scoped:** It runs only once per test session.
-   **Checks for Docker:** It skips the tests gracefully if the Docker daemon is not running.
-   **Automatic Startup:** It runs `docker compose up -d --wait`, which uses the `healthcheck` definitions in `docker-compose.yml` to ensure services are fully ready before tests begin.
-   **No Automatic Cleanup (as per user rule):** The fixture leaves the Docker environment running after tests for manual inspection.

**Example from `tests/conftest.py`:**
```python
@pytest.fixture(scope="session")
def docker_services(request):
    """Manages the Docker environment for the test session."""
    # ... checks for Docker and runs docker compose up --wait ...
    yield
    # ... no cleanup is performed ...
```

This automated setup is crucial for CI/CD environments and ensures that tests are always run against a known, healthy state.
