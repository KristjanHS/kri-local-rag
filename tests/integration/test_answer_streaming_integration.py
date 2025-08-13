import logging as _logging
from unittest.mock import patch

import pytest

import backend.qa_loop as qa_loop

pytestmark = pytest.mark.integration


@patch("backend.qa_loop.generate_response")
@patch("backend.qa_loop.get_top_k")
def test_answer_streaming_output_integration(mock_get_top_k, mock_generate_response, capsys, caplog):
    """Integration test that ensures answer() streams tokens to stdout.

    Uses patched retriever and generator but exercises the public answer flow.
    """
    mock_get_top_k.return_value = ["Some context."]

    def mock_streamer(prompt, model, context, on_token, **kwargs):
        on_token("Hello")
        on_token(" World")
        return "Hello World", None

    mock_generate_response.side_effect = mock_streamer

    caplog.set_level(_logging.ERROR, logger="backend.qa_loop")

    qa_loop.answer("test question")
    captured = capsys.readouterr()
    assert captured.out == "Answer: Hello World\n"
