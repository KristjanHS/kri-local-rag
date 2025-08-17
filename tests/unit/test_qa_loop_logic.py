import logging
from unittest.mock import MagicMock

import pytest

from backend import qa_loop

pytestmark = pytest.mark.unit

# Create a logger for this test file
logger = logging.getLogger(__name__)


def test_rerank_cross_encoder_success(managed_cross_encoder: MagicMock):
    """Test reranking with a successful cross-encoder prediction."""
    logger.debug("--- Running test_rerank_cross_encoder_success ---")
    managed_cross_encoder.predict.return_value = [0.9, 0.1]

    chunks = ["relevant", "irrelevant"]
    question = "test query"

    result = qa_loop._rerank(question, chunks, k_keep=2, cross_encoder=managed_cross_encoder)

    assert len(result) == 2
    assert result[0].text == "relevant"
    assert result[0].score == 0.9
    assert result[1].text == "irrelevant"
    assert result[1].score == 0.1
    managed_cross_encoder.predict.assert_called_once()


def test_rerank_empty_chunks_list(managed_cross_encoder: MagicMock):
    """Test that reranking with an empty list of chunks returns an empty list."""
    result = qa_loop._rerank("test query", [], k_keep=2, cross_encoder=managed_cross_encoder)
    assert result == []
    managed_cross_encoder.predict.assert_not_called()


def test_rerank_model_load_failure_raises_runtime_error():
    """Test that a RuntimeError is raised if the CrossEncoder is not available."""
    with pytest.raises(RuntimeError, match="CrossEncoder model is not available"):
        qa_loop._rerank("test query", ["chunk1"], k_keep=1, cross_encoder=None)
