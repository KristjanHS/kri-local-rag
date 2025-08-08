"""Integration tests for the QA pipeline and retriever."""

from unittest.mock import MagicMock, patch

import pytest

from backend.qa_loop import answer
from backend.retriever import get_top_k

# Mark the entire module as 'slow'
pytestmark = pytest.mark.slow


# -----------------------------------------------------------------------------
# QA pipeline (happy-path) ------------------------------------------------------
# -----------------------------------------------------------------------------


@pytest.mark.integration
@patch("backend.qa_loop.generate_response")
@patch("backend.qa_loop.get_top_k")
def test_qa_pipeline_produces_answer(mock_get_top_k, mock_generate_response):
    """Ensure `answer()` returns a meaningful response and embeds context chunks in the prompt."""
    context_chunk = "France is a country in Western Europe."
    mock_get_top_k.return_value = [context_chunk]

    captured_prompt: list[str] = []

    def _fake_generate_response(prompt, *_, **__):  # noqa: ANN001 – external signature
        captured_prompt.append(prompt)
        return ("The capital of France is Paris.", None)

    mock_generate_response.side_effect = _fake_generate_response

    question = "What is the capital of France?"
    result = answer(question)

    # ─── Assertions ──────────────────────────────────────────────────────────
    assert "Paris" in result
    mock_get_top_k.assert_called_once_with(question, k=60, metadata_filter=None)
    mock_generate_response.assert_called_once()

    # Prompt should contain both the question and the retrieved context
    assert captured_prompt, "Prompt was not captured via generate_response side-effect."
    prompt_text = captured_prompt[0]
    assert question in prompt_text
    assert context_chunk in prompt_text


# -----------------------------------------------------------------------------
# QA pipeline (no context) ------------------------------------------------------
# -----------------------------------------------------------------------------


@pytest.mark.integration
@patch("backend.qa_loop.get_top_k")
def test_qa_pipeline_no_context(mock_get_top_k):
    """`answer()` should return a graceful message when the retriever finds nothing."""
    mock_get_top_k.return_value = []

    question = "What is the capital of France?"
    result = answer(question)

    assert "I found no relevant context" in result
    mock_get_top_k.assert_called_once()


# -----------------------------------------------------------------------------
# Retriever hybrid search parameters ------------------------------------------
# -----------------------------------------------------------------------------


@pytest.mark.integration
@patch("weaviate.connect_to_custom")
def test_get_top_k_hybrid_parameters(mock_connect):
    """Verify that `get_top_k` issues a `hybrid()` query with the expected parameters."""
    # Build a fake Weaviate client->collection->query chain
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_query = MagicMock()
    mock_result = MagicMock()
    mock_obj = MagicMock()
    mock_obj.properties = {"content": "The capital of France is Paris."}
    mock_result.objects = [mock_obj]

    # Wire the mocks together
    mock_query.hybrid.return_value = mock_result
    mock_collection.query = mock_query
    mock_client.collections.get.return_value = mock_collection
    mock_connect.return_value = mock_client

    question = "What is the capital of France?"
    _ = get_top_k(question, k=2)

    # hybrid() should have been called once with correct kwargs
    mock_query.hybrid.assert_called_once()
    kwargs = mock_query.hybrid.call_args.kwargs
    assert kwargs["query"] == question
    assert kwargs["limit"] == 2

    # Client should be closed in the finally block
    mock_client.close.assert_called_once()
