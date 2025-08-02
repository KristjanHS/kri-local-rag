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
from retriever import _get_embedding_model

class TestHybridSearchFix:
    def test_embedding_model_loading(self):
        # ...
```

#### After:
```python
class TestHybridSearchFix:
    def test_embedding_model_loading(self):
        # Import is moved inside the function, so collection is fast
        from retriever import _get_embedding_model
        # ...
```

### Quick Tips for Debugging `pytest`

-   **See `print()` output immediately**: Use `pytest -s` or `pytest --capture=no` to disable output capturing.
-   **Run only fast tests**: Use markers to skip slow or resource-intensive tests.
    1.  **Define markers** in `pytest.ini`:
        ```ini
        [pytest]
        markers =
            slow: marks tests as slow
            docker: tests requiring Docker
        ```
    2.  **Apply markers** in tests: `@pytest.mark.slow`
    3.  **Exclude markers** when running: `pytest -m "not slow and not docker"`

## 2. Improving Terminal Experience with Shell Integration

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
