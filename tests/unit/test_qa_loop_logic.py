import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

# Mock all heavy dependencies before any imports
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["sentence_transformers"].CrossEncoder = MagicMock()

# Mock the config module to avoid .env file loading
mock_config = MagicMock()
mock_config.OLLAMA_MODEL = "test-model"
mock_config.get_logger = MagicMock(return_value=MagicMock())
mock_config.set_log_level = MagicMock()
sys.modules["backend.config"] = mock_config

# Mock other backend modules that might have heavy imports
sys.modules["backend.console"] = MagicMock()
sys.modules["backend.ollama_client"] = MagicMock()
sys.modules["backend.retriever"] = MagicMock()

# Now import the module under test
from backend import qa_loop as qa_loop

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
    """Reset the cached encoder between tests to ensure isolation."""
    if hasattr(qa_loop, "_cached_encoder"):
        delattr(qa_loop, "_cached_encoder")

    # Reset the mock for each test
    sys.modules["sentence_transformers"].CrossEncoder.reset_mock()

    yield

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


def test_rerank_predict_failure_raises_exception():
    """Test that the rerank function raises an exception when predict fails."""
    question = "test question"
    chunks = ["test chunk 1", "chunk 2"]

    # Mock _get_cross_encoder to return a failing encoder
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        mock_encoder = MagicMock()
        mock_encoder.predict.side_effect = Exception("Model prediction failure")
        get_ce.return_value = mock_encoder

        with pytest.raises(Exception, match="Model prediction failure"):
            qa_loop._rerank(question, chunks, k_keep=2)


def test_rerank_encoder_unavailable_raises_exception():
    """Test that the rerank function raises an exception when encoder is unavailable."""
    question = "test question"
    chunks = ["test chunk 1", "chunk 2"]

    # Mock _get_cross_encoder to return None to simulate unavailability
    with patch("backend.qa_loop._get_cross_encoder", return_value=None):
        with pytest.raises(RuntimeError, match="CrossEncoder model is not available"):
            qa_loop._rerank(question, chunks, k_keep=2)


def test_rerank_empty_chunks_list():
    """Test that reranking with an empty list of chunks returns an empty list."""
    # Mock _get_cross_encoder to avoid real model loading
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [0.5]  # Won't be used for empty list
        get_ce.return_value = mock_encoder

        result = qa_loop._rerank("test query", [], k_keep=2)
        assert result == []


def test_keyword_scoring():
    """Test the keyword scoring logic with mocked cross-encoder."""
    question = "test question"
    chunks = ["this is a test chunk", "another chunk"]

    # Mock _get_cross_encoder to return a working encoder
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [0.8, 0.3]  # First chunk more relevant
        get_ce.return_value = mock_encoder

        scored_chunks = qa_loop._score_chunks(question, chunks)

        # Should use cross-encoder scoring
        assert len(scored_chunks) == 2
        assert scored_chunks[0].text == "this is a test chunk"
        assert scored_chunks[0].score == 0.8
        assert scored_chunks[1].text == "another chunk"
        assert scored_chunks[1].score == 0.3


def test_keyword_scoring_no_union():
    """Test the keyword scoring logic when there is no union between the question and chunk."""
    chunks = ["", ""]
    question = ""

    # Mock _get_cross_encoder to return a working encoder
    with patch("backend.qa_loop._get_cross_encoder") as get_ce:
        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [0.5, 0.5]  # Neutral scores
        get_ce.return_value = mock_encoder

        scored_chunks = qa_loop._score_chunks(question, chunks)

        assert len(scored_chunks) == 2
        assert all(sc.score == 0.5 for sc in scored_chunks)


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
