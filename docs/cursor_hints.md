# Troubleshooting and Configuration for Cursor

This guide covers common issues and configurations for a better Python development experience in Cursor, especially on Linux/WSL.

## 1. Fixing `pytest` Hangs

A common issue is `pytest` hanging indefinitely during test collection without any output.

-   **Symptom**: Running `pytest` hangs silently. `Ctrl+C` may also be slow to respond.
-   **Root Cause**: Test collection hangs because `pytest` is importing test files that have slow, top-level imports (e.g., `from sentence_transformers import ...`).
-   **Solution**: Defer heavy imports by moving them from the top of your test files into the specific test functions that need them.

#### Before:
```python
# This top-level import hangs pytest during collection
from backend.models import load_embedder

class TestModelLoading:
    def test_model_loading(self):
        # ...
```

#### After:
```python
class TestModelLoading:
    def test_model_loading(self):
        # Import is moved inside the function, so collection is fast
        from backend.models import load_embedder
        # ...
```

#### Alternative (Recommended):
```python
class TestModelLoading:
    def test_model_loading(self, mock_embedding_model):
        # Use the project's fixture for clean model mocking
        from backend.retriever import _get_embedding_model
        model = _get_embedding_model()
        assert model is not None  # Returns the mock instance
```

## 2. Debugging a "Hanging" Terminal

If a long-running command (like `pytest` or a script) seems to hang or freeze the terminal without any output, it might be due to output buffering. Python often waits to collect a "chunk" of output before displaying it. If the program errors out before a chunk is ready, you will never see the error message.

-   **Symptom**: A command runs for a long time with no output, appearing to be frozen.
-   **Solution**: Force Python to run in "unbuffered" mode using the `-u` flag. This ensures that any `print` statements or errors are displayed in real-time.

-   **Example**:
    ```bash
    # Standard (potentially buffered) command
    python -m pytest

    # Unbuffered command (recommended for debugging)
    python -u -m pytest -sv
    ```

## 3. Improving Terminal Experience with Shell Integration

To unlock powerful terminal features in Cursor, enable shell integration.

-   **Configuration**: Add this line to your `~/.bashrc` file:
    ```bash
    [[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path bash)"
    ```
    *The `[[ "$TERM_PROGRAM" == "vscode" ]]` check ensures this only runs inside Cursor/VS Code.*

-   **Key Benefits**:
    *   **Command Status**: See success/failure icons next to commands.
    *   **Command Navigation**: Jump between commands with `Cmd/Ctrl` + `Up/Down`.
    *   **Smarter Links**: Clickable relative file paths that just work.
    *   **Sticky Scroll**: Current command stays visible at the top as you scroll.
    *   **Better History & Autocomplete**: Improved command history and shell-aware Intellisense.

## 4. Understanding the New Model Loading Architecture

The project has been updated with a centralized, offline-first model loading system. Here are key changes to be aware of:

### Model Loading Functions
- **Old**: Direct imports like `from sentence_transformers import SentenceTransformer`
- **New**: Use centralized loaders: `from backend.models import load_embedder, load_reranker`

### Configuration
- **Centralized**: All model settings in `backend/config.py` with `DEFAULT_*` constants
- **Environment Variables**: Override with `EMBED_REPO`, `RERANK_REPO`, `EMBED_COMMIT`, `RERANK_COMMIT`
- **Offline-First**: Checks for local models first, falls back to downloads with pinned commits

### Testing
- **Preferred**: Use project fixtures like `mock_embedding_model` instead of manual patches
- **Cache Management**: Models are cached in `backend.models` module variables, not individual files

### Common Issues
- **Test Hanging**: Use fixtures or move heavy imports inside test functions
- **Model Not Found**: Ensure proper environment setup or use offline mode
- **Configuration**: Check `backend/config.py` for centralized settings

## 5. Manually Update the Python Extension

Cursor manages its VS Code extension updates, but sometimes they can lag behind the official marketplace. An outdated Microsoft Python (`ms-python.python`) extension is a known cause of strange behavior with `pytest`, including issues with test discovery, execution, and debugging.

-   **Symptom**: Tests fail to run or discover, inconsistent test results, or unexpected debugger behavior.
-   **Solution**: Go to the Extensions tab in Cursor, search for "Python", and manually check for updates for the `ms-python.python` extension. Keeping it on the latest version can resolve many underlying issues.
