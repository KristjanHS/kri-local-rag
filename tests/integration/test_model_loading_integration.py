#!/usr/bin/env python3
"""
Integration tests for real model loading functionality.

Tests the backend.models module with actual model downloads and caching.
Requires network/live models; skips gracefully when they are unavailable.

Marks: slow, requires internet for model downloads
"""

from typing import Any, cast
from unittest.mock import patch

import pytest

from backend.config import get_logger
from backend.models import load_embedder, load_reranker, preload_models

# Type stubs for sentence-transformers (following backend.models.py pattern)
if False:  # typing only - never executed at runtime
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.cross_encoder import CrossEncoder
else:
    SentenceTransformer = Any  # type checker only
    CrossEncoder = Any  # type checker only

# Note: Using cast() for proper type annotations with dynamic model access

# Set up logging
logger = get_logger(__name__)

# Test constants
TEST_SENTENCE = "This is a test sentence for model validation."
EXPECTED_EMBEDDING_DIM = 384  # For all-MiniLM-L6-v2


@pytest.fixture
def reset_global_cache():
    """Reset the global model cache before each test."""
    # Clear the global cache variables
    import backend.models

    backend.models._embedding_model = None
    backend.models._cross_encoder = None
    yield
    # Cleanup happens automatically in the next test


def test_load_embedder_real_model(reset_global_cache):
    """Load the real embedding model and validate its output.

    Skips gracefully when the model cannot be loaded (no network / models
    unavailable in this environment).
    """
    logger.info("Testing real embedding model loading...")

    try:
        model = load_embedder()
    except Exception as e:
        pytest.skip(f"Embedding model unavailable: {e}")

    assert model is not None, "Embedding model should be loaded"

    # Caching: a second load returns the same cached instance.
    model_again = load_embedder()
    assert model is model_again, "Same embedder instance should be returned from cache"

    # Test basic functionality
    embedder_model = cast(SentenceTransformer, model)
    embedding = embedder_model.encode(TEST_SENTENCE)

    # Validate embedding output
    assert embedding.shape == (EXPECTED_EMBEDDING_DIM,), (
        f"Expected shape ({EXPECTED_EMBEDDING_DIM},), got {embedding.shape}"
    )
    assert len(embedding) > 0, "Embedding should not be empty"
    assert embedding.dtype in ["float32", "float64"], f"Unexpected embedding dtype: {embedding.dtype}"

    logger.info("Embedding model loaded and validated successfully")


def test_load_reranker_real_model(reset_global_cache):
    """Load the real reranker model, validate its output, and verify caching.

    Loads the model twice and asserts the second load returns the cached
    instance. Skips gracefully when the model cannot be loaded.
    """
    logger.info("Testing real reranker model loading...")

    try:
        model = load_reranker()
    except Exception as e:
        pytest.skip(f"Reranker model unavailable: {e}")

    assert model is not None, "Reranker model should be loaded"

    # Second load should return the same cached instance
    model_again = load_reranker()
    assert model is model_again, "Same reranker instance should be returned from cache"

    # Test basic functionality with simple query-chunk pairs
    query = "What is machine learning?"
    relevant_chunk = "Machine learning is a subset of artificial intelligence."
    irrelevant_chunk = "The weather is nice today for outdoor activities."

    reranker_model = cast(CrossEncoder, model)
    scores = reranker_model.predict([[query, relevant_chunk], [query, irrelevant_chunk]])

    # Validate reranker output
    assert len(scores) == 2, f"Expected 2 scores, got {len(scores)}"
    assert scores[0] > scores[1], f"Relevant chunk should score higher: {scores[0]} vs {scores[1]}"

    # Check that all scores are numeric (including numpy types)
    def is_numeric(value):
        try:
            # Check for Python numeric types
            if isinstance(value, (int, float)):
                return True
            # Check for numpy numeric types
            if hasattr(value, "dtype"):
                import numpy as np

                return np.issubdtype(value.dtype, np.number)
            # Fallback: try to convert to float
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    assert all(is_numeric(score) for score in scores), f"All scores should be numeric: {scores}"

    logger.info("Reranker model loaded, cached, and validated successfully")


def test_preload_models_functionality(reset_global_cache):
    """Test the preload_models function loads both models correctly."""
    logger.info("Testing preload_models functionality...")

    # Verify models are not loaded initially
    import backend.models

    assert backend.models._embedding_model is None, "Embedding model should not be loaded initially"
    assert backend.models._cross_encoder is None, "Reranker model should not be loaded initially"

    # Preload models
    try:
        preload_models()
    except Exception as e:
        pytest.skip(f"Models unavailable for preload: {e}")

    # Verify both models are now loaded
    assert backend.models._embedding_model is not None, "Embedding model should be loaded after preload"
    assert backend.models._cross_encoder is not None, "Reranker model should be loaded after preload"

    # Test that individual load functions return the preloaded models
    embedder = load_embedder()
    reranker = load_reranker()

    assert embedder is backend.models._embedding_model, "load_embedder should return preloaded model"
    assert reranker is backend.models._cross_encoder, "load_reranker should return preloaded model"

    logger.info("Preload functionality validated successfully")


def test_model_loading_error_handling(reset_global_cache):
    """Test error handling when an invalid model name cannot be loaded."""
    logger.info("Testing model loading error handling...")

    # Test with completely invalid model configuration that will definitely fail
    with patch("backend.models.EMBEDDING_MODEL", "definitely-invalid-model-name-that-cannot-exist"):
        # This should raise an exception because the model name is invalid
        with pytest.raises(Exception) as exc_info:
            load_embedder()

    # Assertions must run AFTER the with-block: code inside pytest.raises after the
    # raising call is unreachable (the exception unwinds out of the block).
    assert exc_info.value is not None, "Should raise an error for invalid model configuration"
    assert isinstance(exc_info.value, (RuntimeError, OSError, Exception)), (
        f"Expected model loading exception, got {type(exc_info.value)}"
    )

    # Verify it's related to missing model or network connectivity (offline mode)
    error_msg = str(exc_info.value).lower()
    expected_keywords = [
        "not found",
        "no such file",
        "cannot find",
        "model",
        "couldn't connect",
        "offline mode",
    ]
    assert any(keyword in error_msg for keyword in expected_keywords), (
        f"Expected missing model or network error, got: {error_msg}"
    )

    logger.info("Error handling validated successfully")
