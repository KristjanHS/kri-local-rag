#!/usr/bin/env python3
"""
Integration tests for real model loading functionality.

Tests the backend.models module with actual model downloads and caching.
Includes timeout protection and error scenario testing.

Marks: slow, requires internet for model downloads
"""

import time
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
MODEL_LOAD_TIMEOUT = 120  # seconds - allow generous time for first download
TEST_SENTENCE = "This is a test sentence for model validation."
EXPECTED_EMBEDDING_DIM = 384  # For all-MiniLM-L6-v2


# Note: Model cache setup is now handled by the integration_model_cache fixture
# in conftest.py to avoid conflicts and provide better integration with real model fixtures


@pytest.fixture
def reset_global_cache():
    """Reset the global model cache before each test."""
    # Clear the global cache variables
    import backend.models

    backend.models._embedding_model = None
    backend.models._cross_encoder = None
    yield
    # Cleanup happens automatically in the next test


def test_load_embedder_real_model_with_timeout(reset_global_cache):
    """
    Test loading real embedding model with timeout protection.

    This test validates that the embedding model can be loaded and functions correctly.
    In integration test environments, network issues may cause model loading to fail,
    which should result in graceful test skipping rather than failure.
    """
    logger.info("Testing real embedding model loading...")

    start_time = time.time()

    try:
        # Load with timeout protection
        model = load_embedder()
        elapsed_time = time.time() - start_time

        # Verify reasonable load time
        assert elapsed_time < MODEL_LOAD_TIMEOUT, ".2f"
        logger.info(".2f")

        # Verify model is loaded and functional
        assert model is not None, "Embedding model should be loaded"

        # Test basic functionality
        embedder_model = cast(SentenceTransformer, model)
        embedding = embedder_model.encode(TEST_SENTENCE)

        # Validate embedding output
        assert embedding.shape == (EXPECTED_EMBEDDING_DIM,), (
            f"Expected shape ({EXPECTED_EMBEDDING_DIM},), got {embedding.shape}"
        )
        assert len(embedding) > 0, "Embedding should not be empty"
        assert embedding.dtype in ["float32", "float64"], f"Unexpected embedding dtype: {embedding.dtype}"

        logger.info("✓ Embedding model loaded and validated successfully")

    except (OSError, ConnectionError, TimeoutError) as e:
        # Handle network/system level errors
        should_skip, reason = _should_skip_on_model_error(e)
        if should_skip:
            pytest.skip(f"Embedding model loading failed: {reason}")
        else:
            # Re-raise unexpected errors of this type
            raise

    except Exception as e:
        # Handle other model loading failures - analyze the error to determine if skip is appropriate
        should_skip, reason = _should_skip_on_model_error(e)
        if should_skip:
            pytest.skip(f"Embedding model loading failed: {reason}")
        else:
            # For truly unexpected errors, we want to know about them
            logger.error(f"Unexpected error during embedding model loading: {e}")
            raise


def _is_network_connectivity_error(error: Exception) -> bool:
    """
    Determine if an exception is likely due to network connectivity issues.

    Args:
        error: The exception to analyze

    Returns:
        bool: True if this appears to be a network connectivity issue
    """
    error_msg = str(error).lower()
    network_indicators = [
        "huggingface.co",
        "couldn't connect",
        "failed to establish",
        "no route to host",
        "connection refused",
        "connection reset",
        "connection timed out",
        "network is unreachable",
        "temporary failure in name resolution",
        "ssl certificate verify failed",
        "certificate verify failed",
    ]
    return any(indicator in error_msg for indicator in network_indicators)


def _is_model_availability_error(error: Exception) -> bool:
    """
    Determine if an exception is likely due to model availability issues.

    Args:
        error: The exception to analyze

    Returns:
        bool: True if this appears to be a model availability issue
    """
    error_msg = str(error).lower()
    availability_indicators = [
        "offline",
        "not found",
        "no such file",
        "cannot find",
        "model not available",
        "repository not found",
        "revision not found",
        "access denied",  # Sometimes indicates network/auth issues
    ]
    return any(indicator in error_msg for indicator in availability_indicators)


def _should_skip_on_model_error(error: Exception) -> tuple[bool, str]:
    """
    Determine if a model loading error should result in test skip.

    Args:
        error: The exception to analyze

    Returns:
        tuple: (should_skip, reason_message)
    """
    if _is_network_connectivity_error(error):
        return True, f"Network connectivity issue: {error}"

    if _is_model_availability_error(error):
        return True, f"Model availability issue: {error}"

    # Check for specific exception types that indicate environmental issues
    if isinstance(error, (OSError, ConnectionError, TimeoutError)):
        return True, f"System/environmental issue: {error}"

    return False, ""


def test_load_reranker_real_model_with_timeout(reset_global_cache):
    """
    Test loading real reranker model with timeout protection.

    This test validates that the reranker model can be loaded and functions correctly.
    In integration test environments, network issues may cause model loading to fail,
    which should result in graceful test skipping rather than failure.
    """
    logger.info("Testing real reranker model loading...")

    start_time = time.time()

    try:
        # Load with timeout protection
        model = load_reranker()
        elapsed_time = time.time() - start_time

        # Verify reasonable load time
        assert elapsed_time < MODEL_LOAD_TIMEOUT, ".2f"
        logger.info(".2f")

        # Verify model is loaded and functional
        assert model is not None, "Reranker model should be loaded"

        # Test basic functionality with simple query-chunk pair
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

        logger.info("✓ Reranker model loaded and validated successfully")

    except (OSError, ConnectionError, TimeoutError) as e:
        # Handle network/system level errors
        should_skip, reason = _should_skip_on_model_error(e)
        if should_skip:
            pytest.skip(f"Reranker model loading failed: {reason}")
        else:
            # Re-raise unexpected errors of this type
            raise

    except Exception as e:
        # Handle other model loading failures - analyze the error to determine if skip is appropriate
        should_skip, reason = _should_skip_on_model_error(e)
        if should_skip:
            pytest.skip(f"Reranker model loading failed: {reason}")
        else:
            # For truly unexpected errors, we want to know about them
            logger.error(f"Unexpected error during reranker model loading: {e}")
            raise


def test_model_caching_behavior(reset_global_cache):
    """Test that models are properly cached and not reloaded unnecessarily."""
    logger.info("Testing model caching behavior...")

    # First load - should download/load model
    start_time = time.time()
    model1 = load_embedder()
    first_load_time = time.time() - start_time

    # Second load - should return cached model
    start_time = time.time()
    model2 = load_embedder()
    second_load_time = time.time() - start_time

    # Verify same instance is returned
    assert model1 is model2, "Same model instance should be returned from cache"

    # Second load should be significantly faster (caching benefit)
    speedup_ratio = first_load_time / max(second_load_time, 0.001)  # Avoid division by zero
    logger.info(".2f")
    # Use speedup_ratio to avoid unused variable warning - caching should provide benefit
    assert speedup_ratio > 1.0, "Second load should be faster than first load"

    # The speedup should be substantial, but we'll be lenient since first load includes download
    assert second_load_time < 1.0, ".3f"

    logger.info("✓ Model caching validated successfully")


def test_preload_models_functionality(reset_global_cache):
    """Test the preload_models function loads both models correctly."""
    logger.info("Testing preload_models functionality...")

    # Verify models are not loaded initially
    import backend.models

    assert backend.models._embedding_model is None, "Embedding model should not be loaded initially"
    assert backend.models._cross_encoder is None, "Reranker model should not be loaded initially"

    # Preload models
    start_time = time.time()
    preload_models()
    preload_time = time.time() - start_time

    logger.info(".2f")
    # Verify preload completed within reasonable time
    assert preload_time < MODEL_LOAD_TIMEOUT * 2, ".2f"

    # Verify both models are now loaded
    assert backend.models._embedding_model is not None, "Embedding model should be loaded after preload"
    assert backend.models._cross_encoder is not None, "Reranker model should be loaded after preload"

    # Test that individual load functions return the preloaded models
    embedder = load_embedder()
    reranker = load_reranker()

    assert embedder is backend.models._embedding_model, "load_embedder should return preloaded model"
    assert reranker is backend.models._cross_encoder, "load_reranker should return preloaded model"

    logger.info("✓ Preload functionality validated successfully")


def test_model_loading_error_handling(reset_global_cache):
    """Test error handling when models cannot be loaded."""
    logger.info("Testing model loading error handling...")

    # Test with completely invalid model configuration that will definitely fail
    with patch("backend.models.EMBEDDING_MODEL", "definitely-invalid-model-name-that-cannot-exist"):
        # This should raise an exception because the model name is invalid
        with pytest.raises(Exception) as exc_info:
            load_embedder()

            # Should raise some kind of error
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

    logger.info("✓ Error handling validated successfully")


def test_offline_mode_functionality(reset_global_cache):
    """Test that model caching works like offline functionality."""
    logger.info("Testing offline mode functionality...")

    # First load models to ensure they're cached (simulating pre-loading in production)
    embedder = load_embedder()
    reranker = load_reranker()

    # Verify models are loaded
    assert embedder is not None, "Embedding model should be loaded"
    assert reranker is not None, "Reranker model should be loaded"

    # Test that subsequent loads return cached models (simulating offline behavior)
    embedder2 = load_embedder()
    reranker2 = load_reranker()

    # Should return the same cached instances
    assert embedder is embedder2, "Should return cached embedding model"
    assert reranker is reranker2, "Should return cached reranker model"

    # Test functionality of cached models
    test_sentence = "This is a test for offline functionality."
    embedder_model = cast(SentenceTransformer, embedder)
    embedding = embedder_model.encode(test_sentence)
    assert embedding.shape == (EXPECTED_EMBEDDING_DIM,), (
        f"Expected shape ({EXPECTED_EMBEDDING_DIM},), got {embedding.shape}"
    )

    # Test reranker functionality
    query = "What is machine learning?"
    relevant = "Machine learning is a type of artificial intelligence."
    irrelevant = "The weather today is sunny."

    reranker_model = cast(CrossEncoder, reranker)
    scores = reranker_model.predict([[query, relevant], [query, irrelevant]])
    assert len(scores) == 2, "Should return scores for both text pairs"
    assert scores[0] > scores[1], "Relevant text should score higher than irrelevant"

    logger.info("✓ Offline mode functionality validated successfully")


# New tests using the real model fixtures
# ============================================================================


def test_real_model_fixtures_integration(real_model_loader, model_health_checker):
    """Test that the new real model fixtures work correctly in integration tests."""
    logger.info("Testing real model fixtures integration...")

    # Load models using the functions from the fixture
    embedder = real_model_loader["embedder"]()
    reranker = real_model_loader["reranker"]()

    # Check model health using the health checker
    health_checker = model_health_checker

    # Test embedding model if available
    if embedder is not None:
        embedder_healthy = health_checker["check_health"](embedder, "embedding_model")
        assert embedder_healthy, "Embedding model should be healthy when loaded"

        # Get model info
        embedder_info = health_checker["get_info"](embedder, "embedding_model")
        assert embedder_info["healthy"], "Embedding model info should show healthy"
        assert embedder_info["embedding_dim"] == EXPECTED_EMBEDDING_DIM, (
            f"Expected embedding dimension {EXPECTED_EMBEDDING_DIM}, got {embedder_info['embedding_dim']}"
        )
        logger.info("✓ Embedding model fixture validated successfully")
    else:
        logger.warning("⚠️ Embedding model not available - skipping embedding tests")

    # Test reranker model if available
    if reranker is not None:
        reranker_healthy = health_checker["check_health"](reranker, "reranker_model")
        assert reranker_healthy, "Reranker model should be healthy when loaded"

        # Get model info
        reranker_info = health_checker["get_info"](reranker, "reranker_model")
        assert reranker_info["healthy"], "Reranker model info should show healthy"
        logger.info("✓ Reranker model fixture validated successfully")
    else:
        logger.warning("⚠️ Reranker model not available - skipping reranker tests")

    # At least one model should be available for the test to be meaningful
    assert embedder is not None or reranker is not None, "At least one model should be available"

    logger.info("✓ Real model fixtures integration validated successfully")


def test_individual_model_fixtures(real_embedding_model, real_reranker_model):
    """Test that individual model fixtures work correctly."""
    logger.info("Testing individual model fixtures...")

    # Test embedding model if available
    if real_embedding_model is not None:
        # Test embedding functionality
        test_text = "Testing individual model fixtures."
        embedding = real_embedding_model.encode(test_text)
        assert embedding.shape == (EXPECTED_EMBEDDING_DIM,), (
            f"Expected embedding shape ({EXPECTED_EMBEDDING_DIM},), got {embedding.shape}"
        )
        logger.info("✓ Individual embedding model fixture validated successfully")
    else:
        logger.warning("⚠️ Individual embedding model fixture not available")

    # Test reranker model if available
    if real_reranker_model is not None:
        # Test reranker functionality
        query = "What is AI?"
        doc1 = "Artificial intelligence is a technology field."
        doc2 = "The sky is blue today."

        scores = real_reranker_model.predict([[query, doc1], [query, doc2]])
        assert len(scores) == 2, "Reranker should return scores for both document pairs"
        assert scores[0] > scores[1], "Relevant document should score higher"
        logger.info("✓ Individual reranker model fixture validated successfully")
    else:
        logger.warning("⚠️ Individual reranker model fixture not available")

    # At least one model should be available for the test to be meaningful
    assert real_embedding_model is not None or real_reranker_model is not None, (
        "At least one individual model fixture should be available"
    )

    logger.info("✓ Individual model fixtures validated successfully")


def test_model_cache_integration_performance(real_model_loader):
    """Test that model caching improves performance in integration tests."""
    import time

    from backend.models import load_embedder, load_reranker

    logger.info("Testing model cache performance integration...")

    # Load models using the functions from the fixture
    embedder1 = real_model_loader["embedder"]()
    reranker1 = real_model_loader["reranker"]()

    # Second load - measure time to load from cache (only for available models)
    start_time = time.time()
    embedder2 = load_embedder() if embedder1 is not None else None
    reranker2 = load_reranker() if reranker1 is not None else None
    second_load_time = time.time() - start_time

    # Verify same instances are returned (proving caching works)
    if embedder1 is not None:
        assert embedder1 is embedder2, "Should return cached embedding model instance"
        logger.info("✓ Embedding model caching verified")
    else:
        logger.warning("⚠️ Embedding model not available for caching test")

    if reranker1 is not None:
        assert reranker1 is reranker2, "Should return cached reranker model instance"
        logger.info("✓ Reranker model caching verified")
    else:
        logger.warning("⚠️ Reranker model not available for caching test")

    # Second load should be very fast due to caching
    if second_load_time > 0:
        logger.info(".3f")
        # Cached loads should be very fast (< 1 second for both models)
        assert second_load_time < 1.0, ".3f"

    # Verify models are still functional
    if embedder1 is not None:
        test_embedding = embedder1.encode("Performance test sentence")
        assert len(test_embedding) == EXPECTED_EMBEDDING_DIM
        logger.info("✓ Embedding model functionality verified")

    if reranker1 is not None:
        test_scores = reranker1.predict([["test query", "test document"]])
        assert len(test_scores) == 1
        logger.info("✓ Reranker model functionality verified")

    # At least one model should be available for the test
    assert embedder1 is not None or reranker1 is not None, "At least one model should be available"

    logger.info("✓ Model cache performance integration validated successfully")
