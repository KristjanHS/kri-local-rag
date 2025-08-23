# Integration Tests Guide

This guide explains how to run integration tests in both Docker and local environments.

## Test Organization

Tests are organized by **folder structure** (not markers):
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests (this folder)
- `tests/e2e/` - End-to-end tests

Pytest automatically discovers tests based on this folder structure, so no additional markers are needed to run integration tests specifically.

## Quick Start

### Option 1: Docker Environment (Recommended)
```bash
# Start test environment (Weaviate + Ollama)
make test-up

# Run all integration tests
make test-run-integration

# Stop test environment
make test-down
```

### Option 2: Local Environment
```bash
# Ensure Weaviate and Ollama are running locally, then:
.venv/bin/python -m pytest tests/integration/ -v

# Or run specific test categories:
.venv/bin/python -m pytest tests/integration/ -m "requires_weaviate" -v
```

## Test Categories

### Service-Specific Tests
```bash
# Tests that require Weaviate
.venv/bin/python -m pytest -m "requires_weaviate" -v

# Tests that require Ollama
.venv/bin/python -m pytest -m "requires_ollama" -v

# Tests that require both services
.venv/bin/python -m pytest -m "requires_weaviate and requires_ollama" -v
```

### Environment-Specific Tests
```bash
# Skip tests that require Docker services
.venv/bin/python -m pytest -m "not docker" -v

# Run only integration tests (folder-based discovery)
.venv/bin/python -m pytest tests/integration/ -v
```

## Writing New Integration Tests

### Service Requirements

Use pytest markers to declare service dependencies:

```python
import pytest

# Method 1: Using pytest markers (recommended)
@pytest.mark.requires_weaviate
def test_my_weaviate_feature():
    """Test that requires Weaviate service."""
    # Test will be automatically skipped if Weaviate unavailable
    pass

@pytest.mark.requires_ollama
def test_my_ollama_feature():
    """Test that requires Ollama service."""
    # Test will be automatically skipped if Ollama unavailable
    pass

@pytest.mark.requires_weaviate
@pytest.mark.requires_ollama
def test_my_multi_service_feature():
    """Test that requires both Weaviate and Ollama."""
    # Test will be automatically skipped if either service unavailable
    pass

# Method 2: Using decorators (legacy, still supported)
from tests.integration.conftest import require_services

@require_services("weaviate")
def test_my_legacy_feature():
    # Test will be skipped if Weaviate unavailable
    pass
```

### Using Fixtures
```python
def test_with_weaviate_client(weaviate_client):
    # Client is automatically connected and cleaned up
    collection = weaviate_client.collections.get("MyCollection")
    # ... use client ...

def test_with_full_environment(integration_test_env):
    env = integration_test_env
    if env['weaviate_available']:
        # Use Weaviate client
        collection = env['weaviate_client'].collections.get("Test")
    if env['ollama_available']:
        # Use Ollama URL
        ollama_url = env['ollama_url']
```

## Troubleshooting

### Common Issues

1. **"Services not available" errors**
   - For Docker: Run `make test-up`
   - For local: Ensure Weaviate and Ollama are running

2. **Connection timeouts**
   - Services might be starting up - wait a moment and retry
   - Check service logs: `make test-logs`

3. **Import errors**
   - Ensure you're in the project root directory
   - Activate virtual environment: `source .venv/bin/activate`

### Environment Detection
```bash
# Check if running in Docker
python -c "from backend.config import is_running_in_docker; print(is_running_in_docker())"

# Check service availability
python -c "from tests.integration.conftest import get_available_services; print(get_available_services())"
```

## Configuration

Integration test settings are in:
- `pyproject.toml` - Service configurations and test markers
- `tests/integration/conftest.py` - Test fixtures and utilities

## Best Practices

1. **Use pytest markers** instead of manual service checking
2. **Leverage fixtures** for automatic connection management
3. **Keep tests simple** - focus on one service requirement at a time
4. **Use descriptive test names** that indicate service requirements
5. **Handle service unavailability gracefully** - tests should skip, not fail

## Examples

See existing tests in `tests/integration/` for examples:
- `test_weaviate_compose.py` - Weaviate-only tests
- `test_qa_real_ollama_compose.py` - Ollama-only tests
- `test_vectorizer_enabled_compose.py` - Multi-service tests
