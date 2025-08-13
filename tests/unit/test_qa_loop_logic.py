from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

import backend.qa_loop as qa_loop

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

        result = qa_loop._rerank(question, chunks, k_keep=2)

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

        result = qa_loop._rerank(question, chunks, k_keep=2)

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

        result = qa_loop._rerank(question, chunks, k_keep=2)

        assert len(result) == 2
        assert result[0].text == "some matching keywords"
        assert result[0].score > result[1].score


def test_rerank_final_fallback_to_neutral_scores(caplog):
    """Test final fallback to neutral scores if all scoring strategies fail."""
    import logging as _logging

    caplog.set_level(_logging.ERROR, logger="backend.qa_loop")
    with mock_encoder_predict_failure():
        with patch("backend.qa_loop.re.findall", side_effect=Exception("Regex failure")):
            chunks = ["chunk1", "chunk2"]
            question = "test query"

            result = qa_loop._rerank(question, chunks, k_keep=2)

            assert len(result) == 2
            assert all(r.score == 0.0 for r in result)
            msgs = [rec.getMessage() for rec in caplog.records]
            assert any("Keyword overlap scoring failed" in m for m in msgs)


def test_rerank_empty_chunks_list():
    """Test that reranking with an empty list of chunks returns an empty list."""
    result = qa_loop._rerank("test query", [], k_keep=2)
    assert result == []


def test_keyword_scoring():
    """Test the keyword scoring logic."""
    with mock_encoder_unavailable():
        chunks = ["some matching keywords", "completely different text"]
        question = "test with matching keywords"

        scored_chunks = qa_loop._score_chunks(question, chunks)

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

        scored_chunks = qa_loop._score_chunks(question, chunks)

        assert len(scored_chunks) == 2
        assert all(sc.score == 0.0 for sc in scored_chunks)
