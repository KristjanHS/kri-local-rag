"""
Model loading utilities following best practices for reproducible, offline-capable deployments.

Based on models_guide.md recommendations:
- Offline-first approach with baked models in production
- Fallback to downloads with pinned commits in development
- Proper error handling and caching
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from backend.config import get_logger

# For manual vectorization - import type only for type-checkers
if False:  # typing only - never executed at runtime
    from sentence_transformers import SentenceTransformer as SentenceTransformerType
    from sentence_transformers.cross_encoder import CrossEncoder as CrossEncoderType
else:
    SentenceTransformerType = object  # runtime fallback for type checkers only
    CrossEncoderType = object

# Module-level cache to avoid reloading models
_embedding_model: Any = None
_cross_encoder: Any = None

# Thread-safe locks for model initialization
_embedder_lock = threading.Lock()
_reranker_lock = threading.Lock()

# Set up logging for this module
logger = get_logger(__name__)

# Integration test configuration
INTEGRATION_TEST_MODE = os.getenv("INTEGRATION_TEST_MODE", "false").lower() == "true"
MODEL_LOAD_TIMEOUT = float(os.getenv("MODEL_LOAD_TIMEOUT", "30.0"))  # seconds
LOCAL_CACHE_PRIORITY = os.getenv("LOCAL_CACHE_PRIORITY", "true").lower() == "true"

# Import model configuration from central config
from backend.config import (
    EMBED_COMMIT,
    EMBED_MODEL_PATH,
    EMBEDDING_MODEL,
    HF_CACHE_DIR,
    RERANK_COMMIT,
    RERANK_MODEL_PATH,
    RERANKER_MODEL,
    TRANSFORMERS_OFFLINE,
)

# Configuration is imported directly from config.py


def load_embedder() -> SentenceTransformerType:
    """
    Load the embedding model with offline-first logic and retry capability.

    Returns:
        SentenceTransformer: The loaded embedding model

    Raises:
        RuntimeError: If model cannot be loaded and no fallback is available
        TimeoutError: If model loading exceeds timeout in integration test mode
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    with _embedder_lock:
        # Double-checked locking to prevent re-initialization
        if _embedding_model is not None:
            return _embedding_model

        try:
            # Import lazily to avoid heavy import-time side effects
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "SentenceTransformer not available. Install with: pip install sentence-transformers"
            ) from e

        start_time = time.time()
        max_retries = 3 if INTEGRATION_TEST_MODE else 1
        last_exception = None

        for attempt in range(max_retries):
            try:
                # In integration test mode with local cache priority, check cache first
                if INTEGRATION_TEST_MODE and LOCAL_CACHE_PRIORITY:
                    # Check if model exists in HuggingFace cache directory
                    cached_model_path = Path(HF_CACHE_DIR) / "hub" / f"models--{EMBEDDING_MODEL.replace('/', '--')}"
                    if cached_model_path.exists():
                        logger.info("Loading embedding model from integration test cache: %s", cached_model_path)
                        try:
                            _embedding_model = SentenceTransformer(str(cached_model_path))
                            logger.debug("Embedding model loaded successfully from integration cache")
                            return _embedding_model
                        except Exception as e:
                            logger.warning(
                                "Failed to load from integration cache, falling back to standard logic: %s", e
                            )

                # Check if baked model exists (production/offline mode)
                if Path(EMBED_MODEL_PATH).exists():
                    logger.info("Loading embedding model from local path: %s", EMBED_MODEL_PATH)
                    _embedding_model = SentenceTransformer(EMBED_MODEL_PATH)
                    logger.debug("Embedding model loaded successfully from local path")
                    return _embedding_model

                # Fallback to downloading with pinned revision (development mode)
                logger.info(
                    "Local embedding model not found, downloading: %s (attempt %d/%d)",
                    EMBEDDING_MODEL,
                    attempt + 1,
                    max_retries,
                )
                if EMBED_COMMIT:
                    logger.debug("Using pinned revision: %s", EMBED_COMMIT)
                    _embedding_model = SentenceTransformer(
                        EMBEDDING_MODEL,
                        cache_folder=HF_CACHE_DIR,
                        revision=EMBED_COMMIT,
                        local_files_only=TRANSFORMERS_OFFLINE,
                    )
                else:
                    logger.warning("No pinned revision found for embedding model")
                    _embedding_model = SentenceTransformer(
                        EMBEDDING_MODEL, cache_folder=HF_CACHE_DIR, local_files_only=TRANSFORMERS_OFFLINE
                    )

                # Check for timeout in integration test mode
                if INTEGRATION_TEST_MODE:
                    load_time = time.time() - start_time
                    if load_time > MODEL_LOAD_TIMEOUT:
                        raise TimeoutError(".2f")

                logger.debug("Embedding model loaded successfully from remote")
                return _embedding_model

            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        "Model loading attempt %d failed: %s. Retrying in %d seconds...", attempt + 1, e, wait_time
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("All %d attempts to load embedding model failed", max_retries)

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Failed to load embedding model after all retries")


def load_reranker() -> CrossEncoderType:
    """
    Load the cross-encoder reranking model with offline-first logic and retry capability.

    Returns:
        CrossEncoder: The loaded reranking model

    Raises:
        RuntimeError: If model cannot be loaded and no fallback is available
        TimeoutError: If model loading exceeds timeout in integration test mode
    """
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder

    with _reranker_lock:
        # Double-checked locking to prevent re-initialization
        if _cross_encoder is not None:
            return _cross_encoder

        try:
            # Import lazily to avoid heavy import-time side effects
            from sentence_transformers.cross_encoder import CrossEncoder  # type: ignore
        except ImportError as e:
            raise RuntimeError("CrossEncoder not available. Install with: pip install sentence-transformers") from e

        start_time = time.time()
        max_retries = 3 if INTEGRATION_TEST_MODE else 1
        last_exception = None

        for attempt in range(max_retries):
            try:
                # In integration test mode with local cache priority, check cache first
                if INTEGRATION_TEST_MODE and LOCAL_CACHE_PRIORITY:
                    # Check if model exists in HuggingFace cache directory
                    cached_model_path = Path(HF_CACHE_DIR) / "hub" / f"models--{RERANKER_MODEL.replace('/', '--')}"
                    if cached_model_path.exists():
                        logger.info("Loading reranker model from integration test cache: %s", cached_model_path)
                        try:
                            _cross_encoder = CrossEncoder(str(cached_model_path))
                            logger.debug("Reranker model loaded successfully from integration cache")
                            return _cross_encoder
                        except Exception as e:
                            logger.warning(
                                "Failed to load from integration cache, falling back to standard logic: %s", e
                            )

                # Check if baked model exists (production/offline mode)
                if Path(RERANK_MODEL_PATH).exists():
                    logger.info("Loading reranker model from local path: %s", RERANK_MODEL_PATH)
                    _cross_encoder = CrossEncoder(RERANK_MODEL_PATH)
                    logger.debug("Reranker model loaded successfully from local path")
                    return _cross_encoder

                # Fallback to downloading with pinned revision (development mode)
                logger.info(
                    "Local reranker model not found, downloading: %s (attempt %d/%d)",
                    RERANKER_MODEL,
                    attempt + 1,
                    max_retries,
                )
                if RERANK_COMMIT:
                    logger.debug("Using pinned revision: %s", RERANK_COMMIT)
                    _cross_encoder = CrossEncoder(
                        RERANKER_MODEL,
                        cache_folder=HF_CACHE_DIR,
                        revision=RERANK_COMMIT,
                        local_files_only=TRANSFORMERS_OFFLINE,
                    )
                else:
                    logger.warning("No pinned revision found for reranker model")
                    _cross_encoder = CrossEncoder(
                        RERANKER_MODEL, cache_folder=HF_CACHE_DIR, local_files_only=TRANSFORMERS_OFFLINE
                    )

                # Check for timeout in integration test mode
                if INTEGRATION_TEST_MODE:
                    load_time = time.time() - start_time
                    if load_time > MODEL_LOAD_TIMEOUT:
                        raise TimeoutError(".2f")

                logger.debug("Reranker model loaded successfully from remote")
                return _cross_encoder

            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        "Reranker model loading attempt %d failed: %s. Retrying in %d seconds...",
                        attempt + 1,
                        e,
                        wait_time,
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("All %d attempts to load reranker model failed", max_retries)

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Failed to load reranker model after all retries")


def preload_models() -> None:
    """
    Preload both models to ensure they're ready for use.
    Useful for testing model availability and warming up caches.
    """
    logger.info("Preloading models...")
    try:
        load_embedder()
        logger.info("✓ Embedding model preloaded")
    except Exception as e:
        logger.error("Failed to preload embedding model: %s", e)

    try:
        load_reranker()
        logger.info("✓ Reranker model preloaded")
    except Exception as e:
        logger.error("Failed to preload reranker model: %s", e)


def preload_models_for_integration_tests() -> None:
    """
    Preload models specifically optimized for integration tests.
    This function prioritizes local cache, has timeout protection, and includes retry logic.
    """
    logger.info("Preloading models for integration tests with retry capability...")
    start_time = time.time()

    # Enable integration test mode if not already set
    original_integration_mode = os.environ.get("INTEGRATION_TEST_MODE")
    if not INTEGRATION_TEST_MODE:
        os.environ["INTEGRATION_TEST_MODE"] = "true"
        # Reload configuration to pick up the new environment variable
        import importlib

        importlib.reload(sys.modules[__name__])
        # Need to use the updated module reference
        from backend.models import INTEGRATION_TEST_MODE as updated_integration_mode

        if not updated_integration_mode:
            logger.warning("Failed to enable integration test mode")

    try:
        load_embedder()
        logger.info("✓ Embedding model preloaded for integration tests")
    except TimeoutError as e:
        logger.error("Embedding model preload timeout: %s", e)
        raise
    except Exception as e:
        logger.error("Failed to preload embedding model for integration tests: %s", e)
        # Don't raise here - allow reranker to still be attempted

    try:
        load_reranker()
        logger.info("✓ Reranker model preloaded for integration tests")
    except TimeoutError as e:
        logger.error("Reranker model preload timeout: %s", e)
        raise
    except Exception as e:
        logger.error("Failed to preload reranker model for integration tests: %s", e)
        # Don't raise here - at least one model might have loaded successfully

    total_time = time.time() - start_time
    logger.info("Integration test model preload completed in %.2f seconds", total_time)

    # Restore original integration test mode
    if original_integration_mode is None:
        os.environ.pop("INTEGRATION_TEST_MODE", None)
    else:
        os.environ["INTEGRATION_TEST_MODE"] = original_integration_mode


def clear_model_cache() -> None:
    """
    Clear the global model cache. Useful for testing to ensure fresh model loading.
    """
    global _embedding_model, _cross_encoder
    _embedding_model = None
    _cross_encoder = None
    logger.info("Model cache cleared")


def preload_models_with_health_check() -> dict:
    """
    Preload models and perform health checks for integration testing.

    Returns:
        dict: Contains status information about model loading and health
    """
    from backend.config import get_logger

    logger = get_logger(__name__)
    status = {
        "embedding_model": {"loaded": False, "healthy": False, "error": None},
        "reranker_model": {"loaded": False, "healthy": False, "error": None},
        "preloaded_at": None,
        "total_time": 0.0,
    }

    start_time = time.time()

    # Enable integration test mode for optimal loading
    original_integration_mode = os.environ.get("INTEGRATION_TEST_MODE")
    if not INTEGRATION_TEST_MODE:
        os.environ["INTEGRATION_TEST_MODE"] = "true"

    try:
        # Load and check embedding model
        try:
            embedder = load_embedder()
            status["embedding_model"]["loaded"] = True

            # Health check
            try:
                test_text = "Health check test sentence"
                embedding = embedder.encode(test_text)  # type: ignore[attr-defined]
                if hasattr(embedding, "shape") and len(embedding.shape) > 0:
                    status["embedding_model"]["healthy"] = True
                    logger.info("✓ Embedding model health check passed")
                else:
                    status["embedding_model"]["error"] = "Invalid embedding output"
                    logger.warning("⚠️ Embedding model health check failed: invalid output")
            except Exception as e:
                status["embedding_model"]["error"] = str(e)
                logger.warning("⚠️ Embedding model health check failed: %s", e)

        except Exception as e:
            status["embedding_model"]["error"] = str(e)
            logger.error("❌ Failed to load embedding model: %s", e)

        # Load and check reranker model
        try:
            reranker = load_reranker()
            status["reranker_model"]["loaded"] = True

            # Health check
            try:
                query = "test query"
                doc = "test document"
                scores = reranker.predict([[query, doc]])  # type: ignore[attr-defined]
                if isinstance(scores, list) and len(scores) > 0:
                    status["reranker_model"]["healthy"] = True
                    logger.info("✓ Reranker model health check passed")
                else:
                    status["reranker_model"]["error"] = "Invalid reranker output"
                    logger.warning("⚠️ Reranker model health check failed: invalid output")
            except Exception as e:
                status["reranker_model"]["error"] = str(e)
                logger.warning("⚠️ Reranker model health check failed: %s", e)

        except Exception as e:
            status["reranker_model"]["error"] = str(e)
            logger.error("❌ Failed to load reranker model: %s", e)

    finally:
        # Restore original integration test mode
        if original_integration_mode is None:
            os.environ.pop("INTEGRATION_TEST_MODE", None)
        else:
            os.environ["INTEGRATION_TEST_MODE"] = original_integration_mode

    # Record timing
    status["total_time"] = time.time() - start_time
    status["preloaded_at"] = time.time()

    logger.info(".2f")
    return status


def get_model_loading_status() -> dict:
    """
    Get current status of model loading for monitoring and debugging.

    Returns:
        dict: Contains current model loading status and cache information
    """
    return {
        "embedding_model_cached": _embedding_model is not None,
        "reranker_model_cached": _cross_encoder is not None,
        "integration_test_mode": INTEGRATION_TEST_MODE,
        "model_load_timeout": MODEL_LOAD_TIMEOUT,
        "local_cache_priority": LOCAL_CACHE_PRIORITY,
        "hf_cache_dir": HF_CACHE_DIR,
        "embedding_model_path": EMBED_MODEL_PATH,
        "reranker_model_path": RERANK_MODEL_PATH,
    }


# For backward compatibility and testing
def get_embedder() -> SentenceTransformerType:
    """Legacy alias for load_embedder()."""
    return load_embedder()


def load_embedder_with_model(model_name: str) -> SentenceTransformerType:
    """
    Load a specific embedding model by name.

    This function is primarily for testing purposes where a specific model needs to be loaded.

    Args:
        model_name: The name of the model to load

    Returns:
        SentenceTransformer: The loaded embedding model

    Raises:
        RuntimeError: If model cannot be loaded and no fallback is available
    """
    try:
        # Import lazily to avoid heavy import-time side effects
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as e:
        raise RuntimeError("SentenceTransformer not available. Install with: pip install sentence-transformers") from e

    # For testing - always create a new instance, don't use global cache
    # Check if baked model exists (production/offline mode)
    if Path(EMBED_MODEL_PATH).exists():
        logger.info("Loading specific embedding model from local path: %s", EMBED_MODEL_PATH)
        return SentenceTransformer(EMBED_MODEL_PATH)

    # Fallback to downloading with pinned revision (development mode)
    logger.info("Local embedding model not found, downloading specific model: %s", model_name)
    if EMBED_COMMIT:
        logger.debug("Using pinned revision: %s", EMBED_COMMIT)
        return SentenceTransformer(
            model_name,
            cache_folder=HF_CACHE_DIR,
            revision=EMBED_COMMIT,
            local_files_only=TRANSFORMERS_OFFLINE,
        )
    else:
        logger.warning("No pinned revision found for embedding model")
        return SentenceTransformer(model_name, cache_folder=HF_CACHE_DIR, local_files_only=TRANSFORMERS_OFFLINE)


def get_cross_encoder() -> CrossEncoderType:
    """Legacy alias for load_reranker()."""
    return load_reranker()
