# Project TODO List

This file tracks outstanding tasks and planned improvements for the project.

## High Priority
- [ ] **Address `vectorizer_config` deprecation warning:** The Weaviate client is showing a deprecation warning for `vectorizer_config`. Research and implement the new `vector_config` to ensure future compatibility.

## Testing and CI/CD
- [ ] **Create environment validation test:** Add a test to the CI pipeline that checks for dependency conflicts (e.g., using `pip check`) to prevent future `protobuf`-style issues.
- [ ] **Add unit test for CLI error handling:** The CLI's error handling was fixed to print to stderr. Add a unit test to assert that exceptions are caught and printed correctly to `sys.stderr`.
- [ ] **Add unit test for automatic model download:** The CLI was updated to call `ensure_model_available`. Add a unit test to verify that this function is called on startup.
- [ ] **Review all integration tests for proper isolation:** Ensure all integration tests use separate resources (like dedicated test collections) and clean up after themselves to prevent flaky tests.

## Code Quality and Refactoring
- [ ] **Refactor Weaviate connection logic:** The logic for connecting to Weaviate is duplicated. Refactor this into a single, reusable function to improve maintainability.
- [ ] **Review and refactor relative paths:** A `Directory not found` error was caused by a relative path. Review the codebase for other instances of relative paths that could cause issues and replace them with absolute paths.

## Logging and Developer Experience
- [ ] **Configure centralized file logging:** The CLI and other processes should log their output to a central file (e.g., `logs/app.log`) so that progress can be monitored and errors can be debugged after the fact.
- [ ] **Enhance progress logging for long-running processes:** Processes like data ingestion should have more detailed, real-time progress logging (e.g., using a progress bar or more frequent log messages) to improve developer experience.

## Documentation
- [ ] **Update DEVELOPMENT.md with dependency management guidelines:** Document the strategy for pinning critical dependencies and how to resolve future conflicts.
- [ ] **Document logging and monitoring strategy in DEVELOPMENT.md:** Add a section to the development guide explaining how logging is configured and where to find logs.

