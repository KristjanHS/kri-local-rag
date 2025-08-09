#!/usr/bin/env python3
"""Frontend smoke test: import Streamlit app with a stubbed streamlit module.

This executes module-level code in `frontend/rag_app.py` without starting Streamlit.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any
from unittest.mock import patch

import pytest


class _StubSidebar:
    def __getattr__(self, name: str) -> Any:  # slider, number_input, markdown, expander, etc.
        if name == "expander":
            return self._expander
        return self._callable

    def _expander(self, *args: Any, **kwargs: Any) -> "_StubSidebar":
        return self

    # Context manager
    def __enter__(self) -> "_StubSidebar":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401
        return False

    def _callable(self, *args: Any, **kwargs: Any) -> Any:
        # Return benign defaults: False/None
        return False


class _StubStreamlit(ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.session_state = _StubSessionState()
        self.sidebar = _StubSidebar()

    def __getattr__(self, name: str) -> Any:  # set_page_config, title, button, form, etc.
        if name in {"set_page_config", "title", "button", "file_uploader", "empty", "expander"}:
            return self._callable
        if name == "form":
            return self._form
        if name == "spinner":
            return self._spinner
        return self._callable

    def _callable(self, *args: Any, **kwargs: Any) -> Any:
        return False

    # Context managers used in the module
    def _form(self, *args: Any, **kwargs: Any):
        return self

    def _spinner(self, *args: Any, **kwargs: Any):
        return self

    def __enter__(self) -> "_StubStreamlit":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401
        return False


class _StubSessionState:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_data":
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value


@pytest.mark.unit
def test_frontend_module_imports_with_stub(monkeypatch) -> None:
    """Test that frontend module can be imported without making real connections."""
    # Inject stubbed streamlit before importing the app
    stub = _StubStreamlit()
    sys.modules["streamlit"] = stub

    # Mock backend initialization to prevent real connections
    with patch("backend.qa_loop.ensure_weaviate_ready_and_populated") as mock_weaviate:
        with patch("backend.ollama_client.ensure_model_available") as mock_ollama:
            # Mock successful initialization
            mock_weaviate.return_value = True
            mock_ollama.return_value = True

            # Import should not trigger any real connections
            mod = __import__("frontend.rag_app", fromlist=["*"])
            assert mod is not None

            # The frontend module calls ensure_weaviate_ready_and_populated during import
            # so we expect it to be called once, but with our mock
            mock_weaviate.assert_called_once()
            mock_ollama.assert_not_called()
