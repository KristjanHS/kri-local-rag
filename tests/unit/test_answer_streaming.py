from unittest.mock import MagicMock, patch

import backend.qa_loop as qa_loop


def test_answer_streams_raw_tokens_and_returns_trimmed():
    """answer() forwards raw tokens to on_token and returns the leading-trimmed full text.

    Presentation (the 'Answer: ' banner, first-token trim, console printing) moved to the
    caller in #8; this pins answer()'s pure streaming contract: raw tokens out, one trim of
    the returned string.
    """
    mock_get_top_k = MagicMock(return_value=["Some context."])

    def mock_streamer(prompt, model, context, on_token, **kwargs):
        # Leading whitespace is preserved in the stream; trimming is a display concern.
        on_token("  Hello")
        on_token(" World")
        return "  Hello World", None

    # Mock the reranker: the real model can't load under the unit tier's socket block.
    cross_encoder = MagicMock()
    cross_encoder.predict.side_effect = lambda pairs: [1.0] * len(pairs)

    streamed: list[str] = []
    with (
        patch("backend.qa_loop.get_top_k", mock_get_top_k),
        patch("backend.qa_loop.generate_response", MagicMock(side_effect=mock_streamer)),
    ):
        result = qa_loop.answer("test question", cross_encoder=cross_encoder, on_token=streamed.append)

    assert streamed == ["  Hello", " World"]
    assert result == "Hello World"
