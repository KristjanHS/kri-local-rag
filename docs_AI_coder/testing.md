# Testing Guide

This guide outlines the testing strategy for the local RAG application, which is designed to ensure code quality, maintainability, and confidence in the system's functionality.

## Test Suites

The test suite is divided into several distinct categories, each serving a specific purpose. This separation allows for targeted testing, faster feedback loops, and clearer intent.

-   **Unit Tests** (`@pytest.mark.unit`): These are fast, isolated tests that verify the correctness of individual functions or classes. They use mocking extensively to remove external dependencies, ensuring they run in seconds.
-   **Integration Tests** (`@pytest.g.integration`): These tests verify the interaction between different components of the application. Some may use `Testcontainers` to spin up real services, providing a realistic testing environment.
-   **End-to-End (E2E) Tests** (`@pytest.mark.e2e`): These tests validate the entire application workflow from start to finish. They are slow and require a fully configured Docker environment.
-   **Docker-Dependent Tests** (`@pytest.mark.docker`): A subset of tests that specifically require a running Docker daemon.
-   **Slow Tests** (`@pytest.mark.slow`): Marks tests that have a significant runtime.
-   **Environment Tests** (`@pytest.mark.environment`): Meta-tests that validate the local development environment.

## Running Tests

By default, running `pytest` will only execute fast tests (unit and integration tests that are not marked as slow). You can, however, select specific test suites using markers.

### Default Test Run (Fast Tests)

This command runs all tests that are not marked as `environment`, `e2e`, or `slow`. It is the standard command to run for most development work.

```bash
.venv/bin/python -m pytest -v
```

### Running Specific Test Suites

You can run specific test suites using the `-m` flag.

-   **Unit Tests Only (Fastest)**

    ```bash
    .venv/bin/python -m pytest -v -m "unit"
    ```

-   **Run All Tests (including slow and E2E)**

    This command runs the entire test suite.

    ```bash
    .venv/bin/python -m pytest -v -m "not environment"
    ```

-   **E2E and Docker Tests Only (Slowest)**

    ```bash
    .venv/bin/python -m pytest -v -m "e2e or docker"
    ```

-   **Environment Sanity Checks**

    Use this command to validate your local development setup.

    ```bash
    .venv/bin/python -m pytest -v -m "environment"
    ```

## Best Practices

-   **Isolate Your Tests**: Ensure unit tests are fast and free of external dependencies. Use integration tests to verify component interactions.
-   **Use Markers**: Leverage pytest markers to organize and selectively run tests.
-   **Mock Strategically**: Mock at the boundaries of your system to isolate the code under test. In unit tests, it's often better to mock a helper function that creates an object rather than the object's class itself.
-   **Write Clear Assertions**: Make your test's intent clear with descriptive assertion messages.

See `tests/unit/test_qa_loop_logic.py` for examples of effective mocking and `tests/integration/test_qa_pipeline.py` for Testcontainer-based integration tests.
