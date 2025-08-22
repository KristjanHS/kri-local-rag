"""
Model loading utilities following best practices for reproducible, offline-capable deployments.

Based on models_guide.md recommendations:
- Offline-first approach with baked models in production
- Fallback to downloads with pinned commits in development
- Proper error handling and caching
"""

from __future__ import annotations

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

# Set up logging for this module
logger = get_logger(__name__)

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
    Load the embedding model with offline-first logic.

    Returns:
        SentenceTransformer: The loaded embedding model

    Raises:
        RuntimeError: If model cannot be loaded and no fallback is available
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        # Import lazily to avoid heavy import-time side effects
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as e:
        raise RuntimeError("SentenceTransformer not available. Install with: pip install sentence-transformers") from e

    # Check if baked model exists (production/offline mode)
    if Path(EMBED_MODEL_PATH).exists():
        logger.info("Loading embedding model from local path: %s", EMBED_MODEL_PATH)
        _embedding_model = SentenceTransformer(EMBED_MODEL_PATH)
        logger.debug("Embedding model loaded successfully from local path")
        return _embedding_model

    # Fallback to downloading with pinned revision (development mode)
    logger.info("Local embedding model not found, downloading: %s", EMBEDDING_MODEL)
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

    logger.debug("Embedding model loaded successfully from remote")
    return _embedding_model


def load_reranker() -> CrossEncoderType:
    """
    Load the cross-encoder reranking model with offline-first logic.

    Returns:
        CrossEncoder: The loaded reranking model

    Raises:
        RuntimeError: If model cannot be loaded and no fallback is available
    """
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder

    try:
        # Import lazily to avoid heavy import-time side effects
        from sentence_transformers.cross_encoder import CrossEncoder  # type: ignore
    except ImportError as e:
        raise RuntimeError("CrossEncoder not available. Install with: pip install sentence-transformers") from e

    # Check if baked model exists (production/offline mode)
    if Path(RERANK_MODEL_PATH).exists():
        logger.info("Loading reranker model from local path: %s", RERANK_MODEL_PATH)
        _cross_encoder = CrossEncoder(RERANK_MODEL_PATH)
        logger.debug("Reranker model loaded successfully from local path")
        return _cross_encoder

    # Fallback to downloading with pinned revision (development mode)
    logger.info("Local reranker model not found, downloading: %s", RERANKER_MODEL)
    if RERANK_COMMIT:
        logger.debug("Using pinned revision: %s", RERANK_COMMIT)
        _cross_encoder = CrossEncoder(
            RERANKER_MODEL, cache_folder=HF_CACHE_DIR, revision=RERANK_COMMIT, local_files_only=TRANSFORMERS_OFFLINE
        )
    else:
        logger.warning("No pinned revision found for reranker model")
        _cross_encoder = CrossEncoder(RERANKER_MODEL, cache_folder=HF_CACHE_DIR, local_files_only=TRANSFORMERS_OFFLINE)

    logger.debug("Reranker model loaded successfully from remote")
    return _cross_encoder


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
