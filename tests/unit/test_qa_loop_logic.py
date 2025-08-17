from unittest.mock import MagicMock

import pytest

from backend import qa_loop

pytestmark = pytest.mark.unit


def test_rerank_cross_encoder_success(mock_cross_encoder: MagicMock):
    """Test reranking with a successful cross-encoder prediction."""
    mock_cross_encoder.return_value.predict.return_value = [0.9, 0.1]
    chunks = ["relevant", "irrelevant"]
    question = "test query"

    result = qa_loop._rerank(question, chunks, k_keep=2)

    assert len(result) == 2
    assert result[0].text == "relevant"
    assert result[0].score == 0.9
    assert result[1].text == "irrelevant"
    assert result[1].score == 0.1
    mock_cross_encoder.return_value.predict.assert_called_once()


def test_rerank_empty_chunks_list(mock_cross_encoder: MagicMock):
    """Test that reranking with an empty list of chunks returns an empty list."""
    result = qa_loop._rerank("test query", [], k_keep=2)
    assert result == []
    mock_cross_encoder.return_value.predict.assert_not_called()


def test_rerank_model_load_failure_raises_runtime_error(mock_cross_encoder: MagicMock):
    """Test that a RuntimeError is raised if the CrossEncoder fails to load."""
    mock_cross_encoder.side_effect = RuntimeError("Failed to load model")

    # Reset the cache to ensure the side_effect is triggered
    qa_loop._cross_encoder = None

    with pytest.raises(RuntimeError, match="Failed to load model"):
        qa_loop._rerank("test query", ["chunk1"], k_keep=1)

    # Restore the cache to avoid side effects on other tests
    qa_loop._cross_encoder = None
