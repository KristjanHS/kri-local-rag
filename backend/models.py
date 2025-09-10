"""
Simple model loading utilities using HuggingFace's built-in caching mechanism.

This module provides a straightforward way to load and cache ML models:
- Automatic caching by HuggingFace transformers
- Module-level caching to avoid reloading
- Clean error handling and logging
"""

from __future__ import annotations

import os

# For manual vectorization - proper type annotations
from typing import Any, TYPE_CHECKING, cast

if TYPE_CHECKING:  # only for type hints; avoids importing at module import time
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.cross_encoder import CrossEncoder

from backend.config import get_logger

# Set up logging for this module early, so the stub can log
logger = get_logger(__name__)

# Ensure text-only Transformers import path in environments without torchvision/compiled ops
# This must be set before any potential transformers imports via sentence-transformers.
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")

# In some environments, importing transformers may indirectly import torchvision and
# fail if compiled ops are unavailable. For our text-only usage, we stub torchvision.
#
# IMPORTANT: This stub is intentionally "fail-fast" at runtime. If any code attempts
# to actually use torchvision functionality (beyond the minimal symbols needed for
# transformers import-time checks), it will raise a RuntimeError with clear guidance.
if os.environ.get("TRANSFORMERS_NO_TORCHVISION", "0") == "1":
    try:
        import sys
        import types
        import importlib.machinery as _machinery

        if "torchvision" not in sys.modules:
            vision_stub = cast(Any, types.ModuleType("torchvision"))
            transforms_stub = cast(Any, types.ModuleType("torchvision.transforms"))
            io_stub = cast(Any, types.ModuleType("torchvision.io"))

            # Provide common module introspection attributes to avoid importlib/inspect pitfalls
            vision_stub.__file__ = "<stub:torchvision>"
            vision_stub.__package__ = "torchvision"
            vision_stub.__path__ = []
            vision_stub.__doc__ = "Stub module for torchvision (text-only environment)"

            transforms_stub.__file__ = "<stub:torchvision.transforms>"
            transforms_stub.__package__ = "torchvision"
            transforms_stub.__path__ = []
            transforms_stub.__doc__ = "Stub module for torchvision.transforms (text-only environment)"

            io_stub.__file__ = "<stub:torchvision.io>"
            io_stub.__package__ = "torchvision"
            io_stub.__path__ = []
            io_stub.__doc__ = "Stub module for torchvision.io (text-only environment)"

            class _InterpolationMode:
                NEAREST = 0
                NEAREST_EXACT = 0
                BILINEAR = 2
                BICUBIC = 3
                BOX = 4
                HAMMING = 5
                LANCZOS = 1

            transforms_stub.InterpolationMode = _InterpolationMode

            # Fail-fast helpers
            def _fail_transforms(name: str = ""):
                raise RuntimeError(
                    (
                        "torchvision.transforms was accessed at runtime but is stubbed. "
                        "This application runs in text-only mode. If you need vision features, "
                        "install working torchvision (matching torch version) and unset "
                        "TRANSFORMERS_NO_TORCHVISION, or isolate vision usage to a separate env. "
                        f"Tried to access: {name or '<unknown>'}"
                    )
                )

            def _fail_io(name: str = ""):
                raise RuntimeError(
                    (
                        "torchvision.io was accessed at runtime but is stubbed. Vision I/O is not supported "
                        "in this environment. Install proper torchvision if required. "
                        f"Tried to access: {name or '<unknown>'}"
                    )
                )

            # Provide __getattr__ to loudly fail on any unresolved attribute access
            def _tv_transforms___getattr__(name: str):
                # Allow only InterpolationMode access; anything else fails
                if name == "InterpolationMode":
                    return transforms_stub.InterpolationMode
                # Permit standard module introspection attributes to be absent gracefully
                if name in {
                    "__file__",
                    "__name__",
                    "__spec__",
                    "__package__",
                    "__loader__",
                    "__path__",
                    "__doc__",
                    "__all__",
                    "__cached__",
                    "__version__",
                }:
                    return None
                return _fail_transforms(name)

            def _tv_io___getattr__(name: str):
                return _fail_io(name)

            transforms_stub.__getattr__ = _tv_transforms___getattr__  # type: ignore[attr-defined]
            io_stub.__getattr__ = _tv_io___getattr__  # type: ignore[attr-defined]

            # Attach submodules to top-level stub
            vision_stub.transforms = transforms_stub
            vision_stub.io = io_stub

            # Provide minimal module specs so importlib checks don't crash
            vision_stub.__spec__ = _machinery.ModuleSpec("torchvision", loader=None)
            transforms_stub.__spec__ = _machinery.ModuleSpec("torchvision.transforms", loader=None)
            io_stub.__spec__ = _machinery.ModuleSpec("torchvision.io", loader=None)

            sys.modules["torchvision"] = vision_stub
            sys.modules["torchvision.transforms"] = transforms_stub
            sys.modules["torchvision.io"] = io_stub
    except Exception as e:
        # Non-fatal: continue without stubbing if anything goes wrong
        # Log at debug level to avoid noisy warnings in normal runs
        logger.debug("Torchvision stub initialization skipped due to error: %s", e, exc_info=True)

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
    logger.info("Embedding model loaded and cached successfully")
    return _embedding_model


def load_reranker() -> "CrossEncoder":
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


def get_model_status() -> dict[str, bool]:
    """Get current status of model loading for monitoring."""
    return {
        "embedding_model_cached": _embedding_model is not None,
        "reranker_model_cached": _cross_encoder is not None,
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
        logger.info("Loading %s model: %s", "embedding" if is_embedding else "reranker", model_name)

        # Lazy import to honor TRANSFORMERS_NO_TORCHVISION before transformers loads
        if is_embedding:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(model_name)
        else:
            from sentence_transformers.cross_encoder import CrossEncoder

            return CrossEncoder(model_name)

    except ImportError as e:
        error_msg = "sentence-transformers not available. Install with: pip install sentence-transformers"
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Could not load model '{model_name}': {e}"
        raise RuntimeError(error_msg) from e


# Legacy aliases for backward compatibility
def get_embedder() -> "SentenceTransformer":
    """Legacy alias for load_embedder()."""
    return load_embedder()


def get_cross_encoder() -> "CrossEncoder":
    """Legacy alias for load_reranker()."""
    return load_reranker()
