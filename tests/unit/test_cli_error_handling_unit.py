from __future__ import annotations

import sys
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit


def test_cli_single_question_reports_error_and_exits(monkeypatch, capsys):
    # Arrange: force single-question path without startup checks
    monkeypatch.setenv("RAG_SKIP_STARTUP_CHECKS", "1")
    monkeypatch.delenv("RAG_FAKE_ANSWER", raising=False)

    # Provide argv for single-question mode
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")  # reduce noisy output in CI
    monkeypatch.setenv("PYTHONUNBUFFERED", "1")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("TERM", "dumb")

    monkeypatch.setattr(sys, "argv", ["cli.py", "--question", "hi"], raising=False)

    # Monkeypatch backend.qa_loop.answer to raise an exception when invoked
    def _raise_answer(*_args, **_kwargs):  # noqa: D401
        raise RuntimeError("boom")

    fake_qa_module = ModuleType("backend.qa_loop")
    fake_qa_module.answer = _raise_answer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "backend.qa_loop", fake_qa_module)
    # Also attach to parent package to ensure import resolution uses the fake
    import backend  # noqa: WPS433 (import for testing)

    monkeypatch.setattr(backend, "qa_loop", fake_qa_module, raising=False)

    # Act + Assert: the CLI should exit with code 1 and print error to stderr
    import cli

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Error:" in err
    assert "boom" in err
