"""E2E test for the CLI script."""

import subprocess
import sys
from unittest.mock import patch

import pytest

# Mark the entire module as 'slow'
pytestmark = pytest.mark.slow


@pytest.mark.e2e
def test_cli_interactive_mode():
    """Test the CLI's interactive mode with a mock question and exit."""
    with patch("backend.qa_loop.answer", return_value="Mocked answer."):
        # Simulate user typing "hello" and then "quit"
        user_input = "hello\nquit\n"
        result = subprocess.run(
            [sys.executable, "cli.py"],
            capture_output=True,
            text=True,
            input=user_input,
            timeout=10,
        )
        # Check for expected output
        assert "RAG System CLI - Interactive Mode" in result.stdout
        assert "Mocked answer." in result.stdout
        assert "Goodbye!" in result.stdout


@pytest.mark.e2e
def test_cli_single_question_mode():
    """Test the CLI's single-question mode."""
    with patch("backend.qa_loop.answer", return_value="Mocked answer for a single question."):
        question = "What is the meaning of life?"
        result = subprocess.run(
            [sys.executable, "cli.py", "--question", question],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Check for expected output
        assert f"Question: {question}" in result.stdout
        assert "Mocked answer for a single question." in result.stdout
