#!/usr/bin/env python3
"""Fixtures for integration tests."""

from __future__ import annotations

import sys

import pytest

## No socket toggling needed for integration suite; sockets are allowed by default.
## Tests that require Docker compose should depend on the `docker_services` fixture explicitly.


## Removed session-wide compose autostart; rely on explicit docker_services usage in tests that need it.


@pytest.fixture(autouse=True)
def _reset_cached_state_between_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset module-level caches and test-affecting env between tests.

    Aligns with guidance in `docs_AI_coder/AI_instructions.md` about cached globals
    causing flaky behavior (e.g., cross-encoder cache). Ensures deterministic mocking
    for `backend.qa_loop` and avoids accidental fake-answer mode.
    """
    # Clear fake-answer env so tests exercise the intended path unless explicitly set
    monkeypatch.delenv("RAG_FAKE_ANSWER", raising=False)

    # Avoid importing modules here to not interfere with patch decorators timing.
    # If modules are already loaded, reset their caches; otherwise skip.
    qa_loop = sys.modules.get("backend.qa_loop")
    if qa_loop is not None:
        try:
            setattr(qa_loop, "_cross_encoder", None)
        except Exception:
            pass
        try:
            setattr(qa_loop, "_ollama_context", None)
        except Exception:
            pass

    retriever = sys.modules.get("backend.retriever")
    if retriever is not None:
        try:
            setattr(retriever, "_embedding_model", None)
        except Exception:
            pass
