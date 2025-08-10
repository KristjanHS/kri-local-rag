from __future__ import annotations

import sys
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit


def test_startup_ensures_model_and_exits_when_missing(monkeypatch, capsys):
    # Force startup checks to run: ensure both skip flags are unset
    monkeypatch.delenv("RAG_SKIP_STARTUP_CHECKS", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # Adjust argv to interactive mode so startup path runs before loop
    monkeypatch.setattr(sys, "argv", ["cli.py"], raising=False)

    # Mock ensure_weaviate_ready_and_populated to no-op via a fake module
    fake_qa_module = ModuleType("backend.qa_loop")

    def _noop_ready():
        return None

    fake_qa_module.ensure_weaviate_ready_and_populated = _noop_ready  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "backend.qa_loop", fake_qa_module)

    # Mock ensure_model_available to return False (model missing) via a fake module
    fake_ollama_module = ModuleType("backend.ollama_client")

    def _ensure_model_available(_model: str) -> bool:  # noqa: ARG001
        return False

    fake_ollama_module.ensure_model_available = _ensure_model_available  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "backend.ollama_client", fake_ollama_module)

    # Ensure OLLAMA_MODEL is something stable
    monkeypatch.setenv("OLLAMA_MODEL", "fake/model")

    # Make sure test path doesn't use fake_answer
    monkeypatch.delenv("RAG_FAKE_ANSWER", raising=False)

    import importlib

    import cli as cli_module

    # Act
    with pytest.raises(SystemExit) as exc:
        importlib.reload(cli_module)
        cli_module.main()

    # Assert
    assert exc.value.code == 1
    assert "Required Ollama model" in capsys.readouterr().err
