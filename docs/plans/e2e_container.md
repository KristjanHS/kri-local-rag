# E2E Test Environment Support

This document tracks the tasks needed to support E2E tests running in both Docker test environment and local environment simultaneously. The TEST_DOCKER environment variable has been eliminated - tests now rely on service URL environment variables for automatic environment detection.

## Background

E2E tests should support both execution modes:
1. **Docker Test Environment**: Tests run inside `app-test` container with Docker internal networking
2. **Local Environment**: Tests run on host machine connecting to services via localhost

Both approaches should work seamlessly using the same test code and service URL environment variables.

## Tasks

### ✅ Completed
- [x] Updated `test-env.sh` to run E2E tests inside `app-test` container
- [x] Modified `cmd_run_e2e()` to use `docker compose exec` instead of `uv run`
- [x] Eliminated TEST_DOCKER environment variable usage
- [x] **Created unified `e2e` fixture mirroring the integration pattern** (`92bd246`)
  - Session-scoped `e2e` fixture in `tests/e2e/conftest.py` exposing
    `config`/`check_service_health`/`require_services`/`get_service_url`
  - Reuses `get_integration_config()` + `is_service_healthy()` from `tests.conftest`
  - Environment auto-detected from the resolved service URL (no TEST_DOCKER —
    already absent from e2e); `require_services` skip-messages pull start commands
    from `[tool.integration.commands]`
  - `pytest_collection_modifyitems` already matched the integration marker-skip
    pattern (no TEST_DOCKER logic to remove)

### 📋 Pending
- [ ] **Migrate existing e2e tests to consume the `e2e` fixture / `require_services`**
  - The fixture is in place but no test opts into it yet (they still gate via
    `requires_weaviate`/`requires_ollama` markers + `*_compose_up` fixtures)

- [ ] **Simplify compose fixtures to match integration test simplicity**
  - Remove complex Docker detection logic
  - Use same service health check approach as integration tests
  - Make fixtures optional and graceful (skip if services unavailable)

- [ ] **Update run_cli_in_container fixture to be environment-aware**
  - Use `app-test` service when running in Docker test environment
  - Provide alternative for local environment execution
  - Follow same pattern as integration test fixtures

- [ ] **Test both execution modes using integration test approach**
  - Verify E2E tests pass in Docker test environment (`make test-e2e`)
  - Verify E2E tests pass in local environment (`make e2e`)
  - Use same service health check logic as integration tests
  - Validate test isolation and cleanup

## Implementation Details

### Follow Integration Test Design Pattern
E2E tests should use the same proven design pattern as integration tests, but without TEST_DOCKER dependencies.

### Key Principles
- Use same service health check and URL resolution logic as integration tests
- Create unified `e2e` fixture similar to integration test's `integration` fixture
- Remove TEST_DOCKER dependencies in favor of service health checks
- Support both Docker and local environments seamlessly
- Use same `get_integration_config()` and `is_service_healthy()` functions

### Container Service Names
- **Test Environment**: `app-test`, `weaviate`, `ollama`
- **Production Environment**: `app`, `weaviate`, `ollama`

## Testing

Run in either environment with the same test code (service URLs auto-resolve, no `TEST_DOCKER`):

- **Docker test env**: `make test-up` → `make test-e2e` → `make test-down`.
- **Local**: start services (`make stack-up`, or run Weaviate/Ollama manually) → `make e2e`
  (teardown controlled by `PRESERVE=0`).

Verify tests pass and check logs for connectivity issues in both modes. Rationale: reusing the
proven integration-test pattern (shared health-check + URL resolution) gives E2E dual-environment
support and closer production parity for free.
