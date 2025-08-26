# Testing Strategy

A high-level guide to testing with real local models and external services.

## Quick Start

### Running Tests by Environment

**Docker Environment (Recommended):**
- Set `TEST_DOCKER=true`
- Run `make test-up` to start services
- Run `make test-run-integration` to execute tests
- Run `make test-down` to stop services

**Local Environment:**
- Set `TEST_DOCKER=false` or leave unset
- Run `.venv/bin/python -m pytest tests/integration/ -v`

### Service-Specific Tests

- **Weaviate only**: `pytest -m "requires_weaviate"`
- **Ollama only**: `pytest -m "requires_ollama"`
- **Both services**: `pytest -m "requires_weaviate and requires_ollama"`

## Core Principles

1. **Test Isolation**: Each test runs independently without state leakage
2. **Real Model Testing**: Use real local models for ML validation, mock external services
3. **Readability**: Clear setup → action → assertion phases in tests
4. **pytest-Native**: Prefer pytest features over unittest patterns

## Test Organization

- `tests/unit/` - Fast, isolated unit tests
- `tests/integration/` - Real models + mocked services
- `tests/e2e/` - Full system validation

## Integration Test Utilities

Integration test utilities are centralized in `tests/integration/conftest.py` to avoid code duplication:

### Core Utility Functions

- **`get_service_url(service)`**: Resolves service URLs based on `TEST_DOCKER` environment variable
- **`is_service_healthy(service)`**: Performs HTTP health checks for services (Weaviate, Ollama)
- **`get_available_services()`**: Returns a dictionary of service availability status

### Usage Pattern

Scripts and tests should import these utilities rather than reimplementing them:

```python
# ✅ Correct: Import from conftest.py
from tests.integration.conftest import (
    get_service_url,
    get_available_services,
    is_service_healthy
)

# ❌ Avoid: Duplicating logic in scripts
def get_service_url(service):  # Duplicate implementation
    # ... implementation
```

### Example: Integration Environment Checker

The `scripts/check_integration_env.py` script demonstrates proper usage by importing utilities from `conftest.py` rather than duplicating the logic.

## Environment Configuration

**Service URLs**: Use explicit environment variables for service endpoints
- `OLLAMA_URL` → Ollama service endpoint (default: `http://localhost:11434`)
- `WEAVIATE_URL` → Weaviate service endpoint (default: `http://localhost:8080`)

**Docker/Compose**: Services automatically set URLs for intra-container communication
- `OLLAMA_URL=http://ollama:11434`
- `WEAVIATE_URL=http://weaviate:8080`

**Local Development**: Use localhost URLs
- `OLLAMA_URL=http://localhost:11434`
- `WEAVIATE_URL=http://localhost:8080`

**Configuration**: Service URLs can be overridden via environment variables

**Health Checks**:
- Weaviate: `{WEAVIATE_URL}/v1/.well-known/ready`
- Ollama: `{OLLAMA_URL}/api/version`

## Key Testing Concepts

### Service-Specific Integration Tests

Tests declare service dependencies using pytest markers and use the `integration` fixture for automatic environment handling.



### Real Models with Mocked Services

Integration tests combine real local models with mocked external services for efficient testing.

### Production Model Smoke Test (Offline)

- Inside the Docker image, models are baked at `EMBED_MODEL_PATH` and `RERANK_MODEL_PATH`.
- We include a simple integration smoke test that verifies these local paths load and run offline.
- Locally (outside Docker), this test skips to keep developer workflow fast.
- To run in Docker tests: `TEST_DOCKER=true make test-up && make test-run-integration && make test-down`.

## Testing Strategy Guidelines

### When to Use Real Models vs Mocks

| Component Type | Recommended Approach | Reasoning |
|---|---|---|---|
| **ML Models** (SentenceTransformer, CrossEncoder) | **Real Local Models** | Need to validate actual model behavior, performance, and component interactions |
| **External Services** (Weaviate, Ollama) | **Mock** | Network calls slow tests, external dependencies unreliable |
| **Database Operations** | **Mock** | Test data isolation, avoid external dependencies |
| **File I/O Operations** | **Mock** | Filesystem operations can be slow and unreliable |
| **Network APIs** | **Mock** | External API calls introduce latency and unreliability |
| **Configuration Systems** | **Real** | Need to test actual config loading and environment variables |

## Best Practices

1. **Cache Management**: Always use fixtures that handle model caching properly
2. **Timeout Handling**: Set reasonable timeouts for model loading operations
3. **Performance Expectations**: Real models are slower than mocks - account for this in test design
4. **Resource Management**: Ensure models are properly cleaned up between tests
5. **Offline Support**: Tests should work in environments without internet connectivity



## Troubleshooting

**Common Issues:**
- **Services not available**: Start services with `make test-up` (Docker) or manually (local)
- **Connection refused**: Verify service URLs match your environment (localhost vs container names)
- **Health check failures**: Services may be starting up, wait and retry
- **Wrong service URLs**: Check environment variables and ensure they match your setup

**Debug Commands:**
- Check service URLs: `echo "OLLAMA_URL=$OLLAMA_URL" && echo "WEAVIATE_URL=$WEAVIATE_URL"`
- Test Weaviate connectivity: `curl -i $WEAVIATE_URL/v1/.well-known/ready`
- Test Ollama connectivity: `curl -i $OLLAMA_URL/api/version`

---

**Note**: This document provides a high-level overview for human readers. For detailed code examples and comprehensive testing guides, see `docs_AI_coder/AI_instructions.md`.
