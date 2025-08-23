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

## Environment Configuration

**Environment Variable**: `TEST_DOCKER`
- `true` → Docker services (`weaviate:8080`, `ollama:11434`)
- `false`/`not set` → Local services (`localhost:8080`, `localhost:11434`)

**Configuration**: Centralized in `pyproject.toml` under `[tool.integration]`

**Health Checks**:
- Weaviate: `http://weaviate:8080/v1/.well-known/ready`
- Ollama: `http://ollama:11434/api/version`

## Key Testing Concepts

### Service-Specific Integration Tests

Tests declare service dependencies using pytest markers and use the `integration` fixture for automatic environment handling.



### Real Models with Mocked Services

Integration tests combine real local models with mocked external services for efficient testing.

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
- **Services not available**: Set `TEST_DOCKER=true` and run `make test-up`
- **Connection refused**: Verify `TEST_DOCKER` setting matches your environment
- **Health check failures**: Services may be starting up, wait and retry

**Debug Commands:**
- Check `TEST_DOCKER` setting: `echo "TEST_DOCKER=$TEST_DOCKER"`
- Test Weaviate connectivity: `curl -i http://localhost:8080/v1/.well-known/ready`
- Test Ollama connectivity: `curl -i http://localhost:11434/api/version`

---

**Note**: This document provides a high-level overview for human readers. For detailed code examples and comprehensive testing guides, see `docs_AI_coder/AI_instructions.md`.
