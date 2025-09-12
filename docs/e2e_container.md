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

### 🔄 In Progress
- [ ] **Update E2E conftest.py to follow integration test design pattern**
  - Create `e2e` fixture similar to integration test's `integration` fixture
  - Use same service health check and URL resolution logic
  - Remove any remaining TEST_DOCKER references
  - Support both Docker and local environments seamlessly

### 📋 Pending
- [ ] **Create unified E2E fixture following integration test pattern**
  - Implement `e2e` fixture with service health checks and URL resolution
  - Use same `get_integration_config()` and `is_service_healthy()` functions
  - Provide `require_services()` function for E2E tests
  - Support both Docker and local environments automatically

- [ ] **Update pytest_collection_modifyitems to match integration test approach**
  - Remove TEST_DOCKER-based logic
  - Use same service health check pattern as integration tests
  - Provide generic error messages (no TEST_DOCKER dependency)

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

## Benefits

1. **Proven Design Pattern**: Uses same successful approach as integration tests
2. **Dual Environment Support**: E2E tests work in both Docker and local environments
3. **Environment Consistency**: Docker tests run in same environment as integration tests
4. **Flexibility**: Developers can choose between Docker or local execution
5. **Dependency Management**: Docker environment has all dependencies pre-installed
6. **Service Connectivity**: Docker uses internal networking, local uses localhost
7. **Production Parity**: Docker tests run in environment closer to production deployment
8. **Simplified Configuration**: No TEST_DOCKER environment variable needed
9. **Automatic Environment Detection**: Service URLs automatically configured by environment
10. **Code Reuse**: Leverages existing integration test infrastructure and patterns

## Testing Strategy

### Docker Test Environment
1. Run `make test-up` to start test environment
2. Run `make test-e2e` to execute E2E tests in container
3. Verify all tests pass and services are accessible
4. Check logs for any connectivity issues
5. Run `make test-down` to clean up

### Local Environment
1. Start services manually (Weaviate, Ollama) or use `make stack-up`
2. Run `make e2e` to execute E2E tests on host
3. Verify all tests pass and services are accessible
4. Check logs for any connectivity issues
5. Optionally run `make stack-down` (controlled by PRESERVE=0)

### Both Environments
- Same test code works in both modes
- Service URLs automatically configured by environment
- No manual environment variable configuration needed

## Notes

- TEST_DOCKER environment variable has been eliminated
- E2E tests should follow the same proven design pattern as integration tests
- Service URLs are automatically configured by environment (Docker Compose or defaults)
- Integration tests already work correctly with container networking
- E2E tests will support both Docker and local execution modes
- No manual environment variable configuration needed
- Service URLs work automatically in both container and host environments
- Developers can choose the execution mode that best fits their workflow
- Will use same service health check and URL resolution logic as integration tests
