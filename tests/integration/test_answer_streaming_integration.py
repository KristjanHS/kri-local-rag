import logging as _logging


import backend.qa_loop as qa_loop


def test_answer_streaming_output_integration(managed_qa_functions, capsys, caplog):
    """Integration test that ensures answer() streams tokens to stdout.

    Uses patched retriever and generator but exercises the public answer flow.
    """
    managed_qa_functions["get_top_k"].return_value = ["Some context."]

    def mock_streamer(prompt, model, context, on_token, **kwargs):
        on_token("Hello")
        on_token(" World")
        return "Hello World", None

    managed_qa_functions["generate_response"].side_effect = mock_streamer

    caplog.set_level(_logging.ERROR, logger="backend.qa_loop")

    qa_loop.answer("test question")
    captured = capsys.readouterr()
    assert captured.out == "Answer: Hello World\n"
