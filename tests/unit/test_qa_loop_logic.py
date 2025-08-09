from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from backend.qa_loop import _rerank, _score_chunks, answer

pytestmark = pytest.mark.unit


@contextmanager
def mock_encoder_success():
    """Mock _get_cross_encoder to return a working encoder."""
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        mock = MagicMock()
        mock.predict.return_value = [0.9, 0.1]
        get_ce.return_value = mock
        yield


@contextmanager
def mock_encoder_predict_failure():
    """Mock _get_cross_encoder to return an encoder that fails on predict."""
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        mock = MagicMock()
        mock.predict.side_effect = Exception("Model prediction failure")
        get_ce.return_value = mock
        yield


@contextmanager
def mock_encoder_unavailable():
    """Mock _get_cross_encoder to return None (encoder unavailable)."""
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        get_ce.return_value = None
        yield


def test_rerank_cross_encoder_success():
    """Test reranking with a successful cross-encoder prediction."""
    with mock_encoder_success():
        chunks = ["relevant", "irrelevant"]
        question = "test query"

        result = _rerank(question, chunks, k_keep=2)

        assert len(result) == 2
        assert result[0].text == "relevant"
        assert result[0].score == 0.9
        assert result[1].text == "irrelevant"
        assert result[1].score == 0.1


def test_rerank_fallback_to_keyword_overlap_on_predict_failure():
    """Test fallback to keyword scoring when cross-encoder.predict() fails."""
    with mock_encoder_predict_failure():
        chunks = ["some matching keywords", "completely different text"]
        question = "test with matching keywords"

        result = _rerank(question, chunks, k_keep=2)

        assert len(result) == 2
        assert result[0].text == "some matching keywords"
        assert result[0].score > 0.0
        assert result[1].text == "completely different text"
        assert result[1].score == 0.0


def test_rerank_fallback_when_encoder_is_unavailable():
    """Test fallback when the cross-encoder model is completely unavailable."""
    with mock_encoder_unavailable():
        chunks = ["some matching keywords", "completely different text"]
        question = "test with matching keywords"

        result = _rerank(question, chunks, k_keep=2)

        assert len(result) == 2
        assert result[0].text == "some matching keywords"
        assert result[0].score > result[1].score


def test_rerank_final_fallback_to_neutral_scores():
    """Test final fallback to neutral scores if all scoring strategies fail."""
    with mock_encoder_predict_failure():
        with patch("backend.qa_loop.re.findall", side_effect=Exception("Regex failure")):
            chunks = ["chunk1", "chunk2"]
            question = "test query"

            result = _rerank(question, chunks, k_keep=2)

            assert len(result) == 2
            assert all(r.score == 0.0 for r in result)


def test_rerank_empty_chunks_list():
    """Test that reranking with an empty list of chunks returns an empty list."""
    result = _rerank("test query", [], k_keep=2)
    assert result == []


def test_keyword_scoring():
    """Test the keyword scoring logic."""
    with mock_encoder_unavailable():
        chunks = ["some matching keywords", "completely different text"]
        question = "test with matching keywords"

        scored_chunks = _score_chunks(question, chunks)

        assert len(scored_chunks) == 2
        assert scored_chunks[0].text == "some matching keywords"
        assert scored_chunks[0].score > 0.0
        assert scored_chunks[1].text == "completely different text"
        assert scored_chunks[1].score == 0.0


def test_keyword_scoring_no_union():
    """Test the keyword scoring logic when there is no union between the question and chunk."""
    with mock_encoder_unavailable():
        chunks = ["", ""]
        question = ""

        scored_chunks = _score_chunks(question, chunks)

        assert len(scored_chunks) == 2
        assert all(sc.score == 0.0 for sc in scored_chunks)


@patch("backend.qa_loop.generate_response")
@patch("backend.qa_loop.get_top_k")
def test_answer_streaming_output(mock_get_top_k, mock_generate_response, capsys):
    """Test that the answer function streams tokens to the console."""
    mock_get_top_k.return_value = ["Some context."]

    # Simulate generate_response calling on_token
    def mock_streamer(prompt, model, context, on_token, **kwargs):
        on_token("Hello")
        on_token(" World")
        return "Hello World", None

    mock_generate_response.side_effect = mock_streamer

    answer("test question")
    captured = capsys.readouterr()
    assert captured.out == "Answer: Hello World\n"
