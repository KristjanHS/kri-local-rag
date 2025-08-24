from __future__ import annotations

import sys
from types import ModuleType

import pytest


def test_startup_ensures_model_and_exits_when_missing(monkeypatch, capsys, caplog):
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
    # Ensure parent package attribute also points to fake module
    import backend  # type: ignore[attr-defined]

    monkeypatch.setattr(backend, "qa_loop", fake_qa_module, raising=False)

    # Mock pull_if_missing to return False (model missing) via a fake module
    fake_ollama_module = ModuleType("backend.ollama_client")

    def _pull_if_missing(_model: str) -> bool:  # noqa: ARG001
        return False

    # Provide both names for backward compatibility in other imports
    fake_ollama_module.pull_if_missing = _pull_if_missing  # type: ignore[attr-defined]
    fake_ollama_module.ensure_model_available = lambda _model: False  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "backend.ollama_client", fake_ollama_module)
    monkeypatch.setattr(backend, "ollama_client", fake_ollama_module, raising=False)

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
    out_err = capsys.readouterr()
    # Message is logged via logger; check both stderr or caplog entries
    text = out_err.err or out_err.out
    if "Required Ollama model" not in text:
        assert any("Required Ollama model" in rec.message for rec in caplog.records)
