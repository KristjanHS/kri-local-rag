"""Unit test for cli.py's streaming presentation.

Covers the 'Answer: ' banner and first-token whitespace trim that moved out of
``backend.qa_loop.answer`` and into ``cli._print_streamed_answer`` (#8).
"""

from __future__ import annotations

from unittest.mock import patch


def test_print_streamed_answer_prefixes_banner_and_trims_first_token(capsys):
    import cli

    def fake_answer(question, k, on_token):
        # First token carries leading whitespace the display must trim.
        on_token("  Hello")
        on_token(" World")
        return "Hello World"

    with patch("backend.qa_loop.answer", side_effect=fake_answer):
        cli._print_streamed_answer("q", 3)

    out = capsys.readouterr().out
    # Banner present, first token left-trimmed (no gap after 'Answer: '), rest verbatim.
    assert "Answer: Hello World" in out
