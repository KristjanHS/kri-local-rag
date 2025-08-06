# Testing Guide

Fast unit tests for ML-heavy RAG application.

## Problem & Solution

**Problem**: ML models (CrossEncoder) take 1-5 minutes to load, stalling tests.

**Solution**: Mock the helper function `_get_cross_encoder()`, not the class.

## Key Pattern

```python
# Production: Skip torch optimizations in tests
skip_optimization = "pytest" in sys.modules or os.getenv("SKIP_TORCH_OPTIMIZATION") == "true"

# Tests: Mock the helper function
@contextmanager
def mock_encoder_success():
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        mock = MagicMock()
        mock.predict.return_value = [0.9, 0.1]
        get_ce.return_value = mock
        yield
```

## Test Scenarios

```python
# Success path
def mock_encoder_success():
    # Returns working encoder with mock.predict.return_value = [0.9, 0.1]

# Predict failure (fallback to keyword scoring)  
def mock_encoder_predict_failure():
    # Returns encoder where mock.predict.side_effect = Exception()

# Model unavailable (graceful degradation)
def mock_encoder_unavailable():
    # Returns None (no encoder available)
```

## Running Tests

```bash
# Unit tests (fast, ~5 seconds)
PYTHONPATH=. .venv/bin/python -m pytest tests/unit/ -v

# Integration tests (slow, real models)
SKIP_TORCH_OPTIMIZATION=false PYTHONPATH=. .venv/bin/python -m pytest tests/integration/ -v
```

## Best Practices

**✅ Do:**
- Mock helper functions (`_get_cross_encoder`) not classes (`CrossEncoder`)
- Use context managers for clean setup
- Test actual fallback behavior
- Keep unit tests < 5 seconds

**❌ Don't:**
- Load real models in unit tests
- Mock too broadly (entire modules)
- Test implementation details
- Modify production code just for tests

See `tests/unit/test_qa_loop_logic.py` for complete examples.