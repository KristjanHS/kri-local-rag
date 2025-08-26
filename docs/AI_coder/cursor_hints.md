# Troubleshooting and Configuration for Cursor

Common issues and configurations for Python development in Cursor on Linux/WSL.

## 1. Fixing `pytest` Hangs

**Symptom**: `pytest` hangs during test collection without output.

**Solution**: Move heavy imports inside test functions.

```python
# ❌ Bad - hangs during collection
from backend.models import load_embedder

class TestModelLoading:
    def test_model_loading(self):
        # ...

# ✅ Good - fast collection
class TestModelLoading:
    def test_model_loading(self):
        from backend.models import load_embedder
        # ...
```

**Recommended**: Use project fixtures instead:
```python
def test_model_loading(self, mock_embedding_model):
    from backend.retriever import _get_embedding_model
    model = _get_embedding_model()
    assert model is not None
```

## 2. Debugging Hanging Commands

**Symptom**: Commands run with no output, appearing frozen.

**Solution**: Use unbuffered mode:
```bash
# Standard (potentially buffered)
python -m pytest

# Unbuffered (recommended for debugging)
python -u -m pytest -sv
```

## 3. Shell Integration

Enable powerful terminal features by adding to `~/.bashrc`:
```bash
[[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path bash)"
```

**Benefits**: Command status icons, navigation, clickable paths, sticky scroll.

## 4. Model Loading Architecture

**Key Changes**:
- Use centralized loaders: `from backend.models import load_embedder, load_reranker`
- Configuration in `backend/config.py` with `DEFAULT_*` constants
- Environment variables: `EMBED_REPO`, `RERANK_REPO`, `EMBED_COMMIT`, `RERANK_COMMIT`
- Offline-first: checks local models first, downloads with pinned commits
- Use project fixtures like `mock_embedding_model` for testing

## 5. Python Extension Updates

**Symptom**: Tests fail to run/discover, inconsistent results, debugger issues.

**Solution**: Manually update the `ms-python.python` extension in Cursor's Extensions tab.
