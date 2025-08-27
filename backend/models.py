"""
Model loading utilities following best practices for reproducible, offline-capable deployments.

Based on models_guide.md recommendations:
- Offline-first approach with baked models in production
- Fallback to downloads with pinned commits in development
- Proper error handling and caching
"""

from __future__ import annotations

# For manual vectorization - proper type annotations
from typing import Any

# Direct imports since sentence-transformers is a required runtime dependency
from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder

from backend.config import get_logger

# Module-level cache to avoid reloading models
_embedding_model: Any = None
_cross_encoder: Any = None

# Set up logging for this module
logger = get_logger(__name__)


# Import model configuration from central config
from backend.config import (
    EMBEDDING_MODEL,
    HF_CACHE_DIR,
    RERANKER_MODEL,
)

# Configuration is imported directly from config.py


def load_embedder() -> SentenceTransformer:
    """Load the embedding model with HuggingFace caching."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    _embedding_model = load_model(EMBEDDING_MODEL, is_embedding=True)
    logger.info("Embedding model loaded and cached successfully")
    return _embedding_model


def load_reranker() -> CrossEncoder:
    """Load the reranker model with HuggingFace caching."""
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder

    _cross_encoder = load_model(RERANKER_MODEL, is_embedding=False)
    logger.info("Reranker model loaded and cached successfully")
    return _cross_encoder


def preload_models() -> None:
    """Preload both models to ensure they're ready for use."""
    logger.info("Preloading models...")
    load_embedder()
    load_reranker()
    logger.info("All models preloaded successfully")


def clear_model_cache() -> None:
    """Clear the global model cache. Useful for testing."""
    global _embedding_model, _cross_encoder
    _embedding_model = None
    _cross_encoder = None
    logger.info("Model cache cleared")


def get_model_status() -> dict:
    """Get current status of model loading for monitoring."""
    return {
        "embedding_model_cached": _embedding_model is not None,
        "reranker_model_cached": _cross_encoder is not None,
        "hf_cache_dir": HF_CACHE_DIR,
    }


def load_model(model_name: str, is_embedding: bool) -> Any:
    """
    Load model using HuggingFace's built-in caching mechanism.

    Args:
        model_name: The name of the model to load
        is_embedding: True for SentenceTransformer, False for CrossEncoder

    Returns:
        The loaded model instance

    Raises:
        RuntimeError: If model cannot be loaded
    """
    try:
        if is_embedding:
            logger.info("Loading embedding model: %s", model_name)
            return SentenceTransformer(model_name)
        else:
            logger.info("Loading reranker model: %s", model_name)
            return CrossEncoder(model_name)
    except ImportError as e:
        error_msg = "sentence-transformers not available. Install with: pip install sentence-transformers"
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Could not load model '{model_name}': {e}"
        raise RuntimeError(error_msg) from e


# Legacy aliases for backward compatibility
def get_embedder() -> SentenceTransformer:
    """Legacy alias for load_embedder()."""
    return load_embedder()


def get_cross_encoder() -> CrossEncoder:
    """Legacy alias for load_reranker()."""
    return load_reranker()
