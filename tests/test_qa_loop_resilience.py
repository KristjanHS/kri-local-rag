from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the project's backend to the Python path to resolve imports
backend_root = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_root))

from qa_loop import _rerank


# Helper to create a mock cross-encoder
def mock_cross_encoder(predict_fn=None):
    encoder = MagicMock()
    if predict_fn:
        encoder.predict = predict_fn
    return encoder


@patch("qa_loop._get_cross_encoder")
def test_rerank_cross_encoder_success(mock_get_encoder):
    """Test reranking with a successful cross-encoder prediction."""
    mock_get_encoder.return_value = mock_cross_encoder(predict_fn=lambda pairs: [0.9, 0.1])

    chunks = ["relevant", "irrelevant"]
    question = "test query"

    result = _rerank(question, chunks, k_keep=2)

    assert len(result) == 2
    assert result[0].text == "relevant"
    assert result[0].score == 0.9
    assert result[1].text == "irrelevant"
    assert result[1].score == 0.1


@patch("qa_loop._get_cross_encoder")
def test_rerank_fallback_to_keyword_overlap_on_predict_failure(mock_get_encoder):
    """Test fallback to keyword scoring when cross-encoder.predict() fails."""
    # Simulate the encoder being available but its predict method failing
    mock_encoder = mock_cross_encoder()
    mock_encoder.predict.side_effect = Exception("Model prediction failure")
    mock_get_encoder.return_value = mock_encoder

    chunks = ["some matching keywords", "completely different text"]
    question = "test with matching keywords"

    result = _rerank(question, chunks, k_keep=2)

    assert len(result) == 2
    # Expect keyword match to have a higher score
    assert result[0].text == "some matching keywords"
    assert result[0].score > 0.0
    assert result[1].text == "completely different text"
    assert result[1].score == 0.0


@patch("qa_loop._get_cross_encoder", return_value=None)
def test_rerank_fallback_when_encoder_is_unavailable(mock_get_encoder):
    """Test fallback when the cross-encoder model is completely unavailable."""
    chunks = ["some matching keywords", "completely different text"]
    question = "test with matching keywords"

    result = _rerank(question, chunks, k_keep=2)

    assert len(result) == 2
    assert result[0].text == "some matching keywords"
    assert result[0].score > result[1].score


@patch("qa_loop._get_cross_encoder")
def test_rerank_final_fallback_to_neutral_scores(mock_get_encoder):
    """Test final fallback to neutral scores if all scoring strategies fail."""
    # Simulate failure in cross-encoder
    mock_encoder = mock_cross_encoder()
    mock_encoder.predict.side_effect = Exception("Model failure")
    mock_get_encoder.return_value = mock_encoder

    # Simulate failure in the keyword fallback logic by patching `re.findall`
    with patch("qa_loop.re.findall", side_effect=Exception("Regex failure")):
        chunks = ["chunk1", "chunk2"]
        question = "test query"

        result = _rerank(question, chunks, k_keep=2)

        assert len(result) == 2
        # All scores should be neutral (0.0)
        assert all(r.score == 0.0 for r in result)


def test_rerank_empty_chunks_list():
    """Test that reranking with an empty list of chunks returns an empty list."""
    result = _rerank("test query", [], k_keep=2)
    assert result == []
