"""Integration tests for the QA pipeline and retriever."""

from unittest.mock import MagicMock

from backend.qa_loop import answer

# Integration tests for QA pipeline functionality


# -----------------------------------------------------------------------------
# QA pipeline (happy-path) ------------------------------------------------------
# -----------------------------------------------------------------------------


def test_qa_pipeline_produces_answer():
    """Ensure `answer()` returns a meaningful response and embeds context chunks in the prompt."""
    context_chunk = "France is a country in Western Europe."
    mock_get_top_k = MagicMock(return_value=[context_chunk])

    captured_prompt: list[str] = []

    def _fake_generate_response(prompt, *_, **__):  # noqa: ANN001 – external signature
        captured_prompt.append(prompt)
        return ("The capital of France is Paris.", None)

    mock_generate_response = MagicMock(side_effect=_fake_generate_response)

    question = "What is the capital of France?"
    from backend.qa_loop import _get_cross_encoder

    cross_encoder = _get_cross_encoder()
    result = answer(
        question,
        cross_encoder=cross_encoder,
        get_top_k_func=mock_get_top_k,
        generate_response_func=mock_generate_response,
    )

    # ─── Assertions ──────────────────────────────────────────────────────────
    assert "Paris" in result
    mock_get_top_k.assert_called_once_with(
        question, k=60, metadata_filter=None, embedding_model=None, collection_name=None
    )
    mock_generate_response.assert_called_once()

    # Prompt should contain both the question and the retrieved context
    assert captured_prompt, "Prompt was not captured via generate_response side-effect."
    prompt_text = captured_prompt[0]
    assert question in prompt_text
    assert context_chunk in prompt_text


# -----------------------------------------------------------------------------
# QA pipeline (no context) ------------------------------------------------------
# -----------------------------------------------------------------------------


def test_qa_pipeline_no_context():
    """`answer()` should return a graceful message when the retriever finds nothing."""
    mock_get_top_k = MagicMock(return_value=[])

    question = "What is the capital of France?"
    from backend.qa_loop import _get_cross_encoder

    cross_encoder = _get_cross_encoder()
    result = answer(question, cross_encoder=cross_encoder, get_top_k_func=mock_get_top_k)

    assert "I found no relevant context" in result
    mock_get_top_k.assert_called_once()


"""
The specific hybrid-parameter verification is covered in unit tests.
This integration module focuses on QA pipeline behavior.
"""
