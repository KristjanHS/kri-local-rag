"""E2E tests for the CLI script (smoke-level, no external deps).

These tests are designed to be deterministic and fast by leveraging
CLI test hooks controlled via environment variables:
- RAG_SKIP_STARTUP_CHECKS=1   → skip slow readiness checks
- RAG_FAKE_ANSWER=...         → bypass network/model calls
- RAG_VERBOSE_TEST=1          → print phase banners for traceability
"""

import os
import subprocess
import sys

import pytest

# Mark the entire module as 'slow' (still quick, but consistent with e2e label)
pytestmark = pytest.mark.slow


@pytest.mark.e2e
def test_cli_interactive_mode():
    """Interactive mode: provide a question and then quit.

    Uses env hooks to ensure no external calls and clear progress output.
    """
    env = {
        **os.environ,
        "RAG_SKIP_STARTUP_CHECKS": "1",
        "RAG_FAKE_ANSWER": "Mocked answer.",
        "RAG_VERBOSE_TEST": "1",
    }
    # Simulate user typing "hello" and then "quit"
    user_input = "hello\nquit\n"
    with open("reports/logs/e2e_cli_interactive.out", "w", encoding="utf-8") as out:
        result = subprocess.run(
            [sys.executable, "cli.py"],
            stdout=out,
            stderr=subprocess.STDOUT,
            text=True,
            input=user_input,
            timeout=10,
            env=env,
        )
    # Check for expected output (from captured file)
    with open("reports/logs/e2e_cli_interactive.out", "r", encoding="utf-8") as f:
        out = f.read()
    assert "PHASE: interactive" in out
    assert "RAG System CLI - Interactive Mode" in out
    assert "Mocked answer." in out
    assert "Goodbye!" in out
    assert result.returncode == 0


@pytest.mark.e2e
def test_cli_single_question_mode():
    """Single-question mode with a deterministic fake answer."""
    env = {
        **os.environ,
        "RAG_SKIP_STARTUP_CHECKS": "1",
        "RAG_FAKE_ANSWER": "Mocked answer for a single question.",
        "RAG_VERBOSE_TEST": "1",
    }
    question = "What is the meaning of life?"
    with open("reports/logs/e2e_cli_single.out", "w", encoding="utf-8") as out:
        result = subprocess.run(
            [sys.executable, "cli.py", "--question", question],
            stdout=out,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
            env=env,
        )
    # Check for expected output (from captured file)
    with open("reports/logs/e2e_cli_single.out", "r", encoding="utf-8") as f:
        out = f.read()
    assert "PHASE: single_question" in out
    assert f"Question: {question}" in out
    assert "Answer: Mocked answer for a single question." in out
    assert result.returncode == 0
