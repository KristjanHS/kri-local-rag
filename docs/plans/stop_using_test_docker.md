# Eliminate TEST_DOCKER Environment Variable

This document outlines the plan to eliminate the `TEST_DOCKER` environment variable and replace it with a more robust environment-based detection system that relies on service URL environment variables.

## Current State

The `TEST_DOCKER` environment variable is currently used in:
- `backend/config.py` - `is_running_in_docker()` function
- `tests/integration/conftest.py` - Environment detection
- `scripts/dev/test-env.sh` - Setting environment for container tests
- Various documentation files

## Problems with TEST_DOCKER

1. **Redundant**: We already have `WEAVIATE_URL` and `OLLAMA_URL` environment variables
2. **Manual**: Requires explicit setting in test scripts
3. **Error-prone**: Easy to forget or set incorrectly
4. **Inconsistent**: Different behavior between integration and E2E tests

## Proposed Solution

**Eliminate TEST_DOCKER entirely** - no detection function needed!

The service URL environment variables (`WEAVIATE_URL`, `OLLAMA_URL`) already contain all the information we need:

- **Container environment**: `WEAVIATE_URL=http://weaviate:8080`, `OLLAMA_URL=http://ollama:11434`
- **Host environment**: `WEAVIATE_URL=http://localhost:8080`, `OLLAMA_URL=http://localhost:11434`

Tests can simply use the service URLs directly without any environment detection.

## Tasks

### ✅ Completed
- [x] Identified all TEST_DOCKER usage across codebase (40 occurrences)

### 🔄 In Progress
- [ ] **Audit all TEST_DOCKER usage across the codebase**
  - Document current usage patterns
  - Identify replacement strategies for each location

### 📋 Pending
- [ ] **Remove TEST_DOCKER checks entirely**
  - Delete `is_running_in_docker()` function from `backend/config.py`
  - Remove all TEST_DOCKER environment variable checks
  - Use service URLs directly in all code

- [ ] **Update backend/config.py to remove is_running_in_docker() function**
  - Delete the function completely
  - Remove TEST_DOCKER dependency
  - No replacement needed - just use service URLs directly

- [ ] **Modify test fixtures to remove TEST_DOCKER dependencies**
  - Update `tests/integration/conftest.py` to remove TEST_DOCKER checks
  - Update `tests/e2e/conftest.py` to remove TEST_DOCKER checks
  - Use generic error messages instead of environment-specific ones

- [ ] **Update test scripts to remove TEST_DOCKER environment variable setting**
  - Remove `-e TEST_DOCKER=true` from `test-env.sh`
  - Update Makefile targets if needed
  - Ensure tests work without explicit TEST_DOCKER setting

- [ ] **Update documentation to reflect new environment-based approach**
  - Update `docs/dev_test_CI/testing_approach.md`
  - Update `docs/dev_test_CI/DEVELOPMENT.md`
  - Update `docs/AI_coder/AI_instructions.md`
  - Remove TEST_DOCKER references from all docs

- [ ] **Test the updated configuration without TEST_DOCKER variable**
  - Run integration tests in container environment
  - Run E2E tests in container environment
  - Run tests on host environment
  - Verify proper environment detection

## Implementation Details

### No Detection Function Needed!

Instead of creating a detection function, just use the service URLs directly:

```python
# Before (with TEST_DOCKER):
if is_running_in_docker():
    # Container logic
else:
    # Host logic

# After (no detection needed):
# Just use the service URLs directly - they already contain the right values!
weaviate_url = get_service_url("weaviate")  # Works in both environments
ollama_url = get_service_url("ollama")      # Works in both environments
```

### Service URL Patterns

| Environment | WEAVIATE_URL | OLLAMA_URL | Detection |
|-------------|--------------|------------|-----------|
| **Container** | `http://weaviate:8080` | `http://ollama:11434` | ✅ Container |
| **Host** | `http://localhost:8080` | `http://localhost:11434` | ❌ Host |
| **Custom** | `http://custom:8080` | `http://custom:11434` | ✅ Container |

### Migration Strategy

1. **Phase 1**: Remove `-e TEST_DOCKER=true` from test scripts
2. **Phase 2**: Delete `is_running_in_docker()` function from `backend/config.py`
3. **Phase 3**: Remove TEST_DOCKER checks from test fixtures
4. **Phase 4**: Update error messages to be generic
5. **Phase 5**: Update documentation

## Benefits

1. **No Detection Needed**: Service URLs already contain the right values
2. **Simpler**: No environment detection logic required
3. **More Reliable**: No risk of TEST_DOCKER being set incorrectly
4. **12-Factor Compliant**: Uses environment variables for configuration
5. **Fewer Variables**: One less environment variable to manage

## Files to Update

### Core Code
- `backend/config.py` - Delete `is_running_in_docker()` function
- `tests/integration/conftest.py` - Remove TEST_DOCKER checks
- `tests/e2e/conftest.py` - Remove TEST_DOCKER checks

### Scripts
- `scripts/dev/test-env.sh` - Remove TEST_DOCKER setting
- `Makefile` - Update test targets if needed

### Documentation
- `docs/dev_test_CI/testing_approach.md`
- `docs/dev_test_CI/DEVELOPMENT.md`
- `docs/AI_coder/AI_instructions.md`
- `docs/e2e_container.md` - Update to reflect new approach

### Tests
- `tests/unit/test_python_setup.py` - Update skip condition
- Any other tests that reference TEST_DOCKER

## Testing Strategy

1. **Container Environment**:
   ```bash
   make test-up
   make test-integration
   make test-e2e
   make test-down
   ```

2. **Host Environment**:
   ```bash
   # Start services manually
   docker run -d -p 8080:8080 semitechnologies/weaviate:latest
   ollama serve
   
   # Run tests
   make integration
   make e2e
   ```

3. **Verification**:
   - Check that environment detection works correctly
   - Verify service connectivity in both environments
   - Ensure no TEST_DOCKER references remain

## Rollback Plan

If issues arise, we can temporarily restore TEST_DOCKER usage by:
1. Reverting `backend/config.py` changes
2. Re-adding `-e TEST_DOCKER=true` to test scripts
3. Updating test fixtures to use TEST_DOCKER again

## Success Criteria

- [ ] All tests pass without TEST_DOCKER environment variable
- [ ] Service URLs work correctly in both container and host environments
- [ ] No TEST_DOCKER references remain in codebase
- [ ] Documentation updated to reflect new approach
- [ ] CI/CD pipelines work without modification
