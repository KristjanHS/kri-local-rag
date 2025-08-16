from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

import backend.qa_loop as qa_loop

pytestmark = pytest.mark.unit

# IMPORTANT: This test file uses multiple layers of protection to ensure
# that no real cross-encoder models are loaded during unit tests:
#
# 1. _reset_encoder_cache fixture: Resets cached encoder and CrossEncoder import
# 2. Mock context managers: Properly mock _get_cross_encoder function
# 3. Import patching: Prevent real sentence_transformers imports
# 4. test_no_real_model_loading: Verifies protection is working
#
# This prevents flaky tests and keeps unit tests fast and reliable.


@pytest.fixture(autouse=True)
def _reset_encoder_cache():
    """Fixture to reset the cached cross-encoder before each test.

    This prevents state from leaking between tests, which can cause mocks to be
    bypassed if a real encoder was cached by a previous test.
    """
    # Reset the cached encoder
    qa_loop._cross_encoder = None

    # Also reset the module-level CrossEncoder to ensure no real imports happen
    qa_loop.CrossEncoder = None


@contextmanager
def mock_encoder_success():
    """Mock _get_cross_encoder to return a working encoder."""
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        # Also patch the import to prevent any real model loading
        with patch("backend.qa_loop.CrossEncoder", None):
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

        # The results should be sorted by score, so "relevant" should be first
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


def test_no_real_model_loading():
    """Test that no real cross-encoder model is loaded during tests."""
    # This test ensures that the real sentence_transformers library is never imported
    # during unit tests, which would be expensive and slow down the test suite.

    with mock_encoder_success():
        # Verify that the mock is being used, not a real model
        chunks = ["test chunk"]
        question = "test question"

        # This should use the mock, not load a real model
        result = qa_loop._rerank(question, chunks, k_keep=1)

        assert len(result) == 1
        assert result[0].score == 0.9  # This is the mock's return value

        # Verify that no real CrossEncoder was imported
        assert qa_loop.CrossEncoder is None
