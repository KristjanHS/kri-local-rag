"""Integration smoke tests for the CLI script entrypoint.

Scope (be honest about what this covers):
These tests run ``cli.py`` as a real subprocess to exercise the *entrypoint
wiring* — the ``__main__`` → ``sys.exit(main())`` boundary, argparse parsing of
real ``argv``, the interactive ``input()`` loop, and the ``RAG_FAKE_ANSWER`` test
hook plumbing — end to end through a separate process.

They deliberately do NOT exercise the real RAG path (retrieval, embeddings,
Ollama/Weaviate). The ``RAG_FAKE_ANSWER`` hook short-circuits the answer with an
injected constant and ``RAG_SKIP_STARTUP_CHECKS`` bypasses readiness probes, so
the test is deterministic and runs fully offline. The assertions on the injected
answer string only verify that the fake-answer hook is honored through the
subprocess — they are NOT a check of answer quality or real model output.

Real-service coverage lives in the e2e tier
(``tests/e2e/test_qa_real_end_to_end_container_e2e.py``); the error/exception
branch of ``main()`` is covered in-process by
``tests/unit/test_cli_error_handling_unit.py``.

Env hooks used:
- RAG_SKIP_STARTUP_CHECKS=1   → skip slow readiness checks (offline)
- RAG_FAKE_ANSWER=...         → bypass network/model calls with a fixed answer
- RAG_VERBOSE_TEST=1          → emit phase banners for traceability
"""

import os
import subprocess
import sys


def _cli_env(fake_answer: str) -> dict[str, str]:
    return {
        **os.environ,
        "RAG_SKIP_STARTUP_CHECKS": "1",
        "RAG_FAKE_ANSWER": fake_answer,
        "RAG_VERBOSE_TEST": "1",
    }


def test_cli_entrypoint_interactive_mode_honors_fake_answer_hook():
    """Interactive entrypoint: feed a question then quit, via a real subprocess.

    Verifies the ``__main__`` wiring, the interactive ``input()`` loop, and that
    the ``RAG_FAKE_ANSWER`` hook is plumbed through to the printed answer.
    """
    result = subprocess.run(
        [sys.executable, "cli.py"],
        capture_output=True,
        text=True,
        input="hello\nquit\n",
        timeout=30,
        env=_cli_env("Mocked answer."),
    )
    out = result.stdout + result.stderr
    # Entrypoint/argparse wiring reached interactive mode:
    assert "PHASE: interactive" in out
    assert "RAG System CLI - Interactive Mode" in out
    # Fake-answer hook honored through the subprocess (injected constant, not a real answer):
    assert "Mocked answer." in out
    assert "Goodbye!" in out
    assert result.returncode == 0


def test_cli_entrypoint_single_question_mode_honors_fake_answer_hook():
    """Single-question entrypoint: ``--question`` parsed from real argv via subprocess.

    Verifies argparse handling of ``--question`` and that the ``RAG_FAKE_ANSWER``
    hook is plumbed through to the printed answer.
    """
    question = "What is the meaning of life?"
    result = subprocess.run(
        [sys.executable, "cli.py", "--question", question],
        capture_output=True,
        text=True,
        timeout=30,
        env=_cli_env("Mocked answer for a single question."),
    )
    out = result.stdout + result.stderr
    assert "PHASE: single_question" in out
    assert f"Question: {question}" in out
    # Fake-answer hook honored through the subprocess (injected constant, not a real answer):
    assert "Answer: Mocked answer for a single question." in out
    assert result.returncode == 0
