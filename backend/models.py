"""
Simple model loading utilities using HuggingFace's built-in caching mechanism.

This module provides a straightforward way to load and cache ML models:
- Automatic caching by HuggingFace transformers
- Module-level caching to avoid reloading
- Clean error handling and logging
"""

from __future__ import annotations

# For manual vectorization - proper type annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # only for type hints; avoids importing at module import time
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.cross_encoder import CrossEncoder

from backend.config import get_logger

logger = get_logger(__name__)

# Module-level cache to avoid reloading models
_embedding_model: Any = None
_cross_encoder: Any = None


# Import model configuration from central config
from backend.config import (
    EMBEDDING_MODEL,
    RERANKER_MODEL,
)

# Configuration is imported directly from config.py


def load_embedder() -> "SentenceTransformer":
    """Load the embedding model with HuggingFace caching."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    _embedding_model = load_model(EMBEDDING_MODEL, is_embedding=True)
    logger.debug("Embedding model loaded and cached successfully")
    return _embedding_model


def load_reranker() -> "CrossEncoder":
    """Load the reranker model with HuggingFace caching."""
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder

    _cross_encoder = load_model(RERANKER_MODEL, is_embedding=False)
    logger.debug("Reranker model loaded and cached successfully")
    return _cross_encoder


def preload_models() -> None:
    """Preload both models to ensure they're ready for use."""
    logger.info("Preloading models...")
    load_embedder()
    load_reranker()
    logger.debug("All models preloaded successfully")


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
        logger.info("Loading %s model: %s", "embedding" if is_embedding else "reranker", model_name)

        # Lazy import so the heavy sentence-transformers/torch stack only loads on first use.
        if is_embedding:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(model_name)
        else:
            from sentence_transformers.cross_encoder import CrossEncoder

            return CrossEncoder(model_name)

    except ImportError as e:
        error_msg = "sentence-transformers not available. Install with: make uv-sync-test"
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Could not load model '{model_name}': {e}"
        raise RuntimeError(error_msg) from e
