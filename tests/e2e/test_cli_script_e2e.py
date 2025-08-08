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
    result = subprocess.run(
        [sys.executable, "cli.py"],
        capture_output=True,
        text=True,
        input=user_input,
        timeout=10,
        env=env,
    )
    # Check for expected output
    assert "PHASE: interactive" in result.stdout
    assert "RAG System CLI - Interactive Mode" in result.stdout
    assert "Mocked answer." in result.stdout
    assert "Goodbye!" in result.stdout


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
    result = subprocess.run(
        [sys.executable, "cli.py", "--question", question],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    # Check for expected output
    assert "PHASE: single_question" in result.stdout
    assert f"Question: {question}" in result.stdout
    assert "Answer: Mocked answer for a single question." in result.stdout
