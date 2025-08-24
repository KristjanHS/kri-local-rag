import logging as _logging
from unittest.mock import MagicMock


import backend.qa_loop as qa_loop


def test_answer_streaming_output_integration(capsys, caplog):
    """Integration test that ensures answer() streams tokens to stdout.

    Uses patched retriever and generator but exercises the public answer flow.
    """
    mock_get_top_k = MagicMock(return_value=["Some context."])

    def mock_streamer(prompt, model, context, on_token, **kwargs):
        on_token("Hello")
        on_token(" World")
        return "Hello World", None

    mock_generate_response = MagicMock(side_effect=mock_streamer)

    caplog.set_level(_logging.ERROR, logger="backend.qa_loop")

    cross_encoder = qa_loop._get_cross_encoder()
    qa_loop.answer(
        "test question",
        cross_encoder=cross_encoder,
        get_top_k_func=mock_get_top_k,
        generate_response_func=mock_generate_response,
    )
    captured = capsys.readouterr()
    # The output may contain logging messages, so we check for the expected answer
    assert "Answer: Hello World" in captured.out
