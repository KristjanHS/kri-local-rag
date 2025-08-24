#!/usr/bin/env python3
"""
Integration smoke test to validate that baked local model paths work offline.

This test is designed to run inside the Docker image where models are baked at
EMBED_MODEL_PATH and RERANK_MODEL_PATH. It skips when those paths are absent
so local dev (outside Docker) remains simple and fast.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from backend.config import EMBED_MODEL_PATH, RERANK_MODEL_PATH
from backend.models import clear_model_cache, load_embedder, load_reranker

# Type stubs for sentence-transformers (avoid heavy imports at module import time)
if False:  # typing only - never executed at runtime
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.cross_encoder import CrossEncoder
else:
    SentenceTransformer = Any  # type checker only
    CrossEncoder = Any  # type checker only


pytestmark = [pytest.mark.integration]


def test_models_load_from_local_paths_offline(monkeypatch: pytest.MonkeyPatch):
    """Ensure models load successfully from baked local paths with offline mode forced.

    Skips if local paths are not present (e.g., running outside the Docker image).
    """
    embed_path = Path(EMBED_MODEL_PATH)
    rerank_path = Path(RERANK_MODEL_PATH)

    if not embed_path.exists() or not rerank_path.exists():
        pytest.skip("Local baked model paths not present; run inside Docker image with baked models.")

    # Force offline mode to ensure we do not hit the network and require baked paths
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    clear_model_cache()

    embedder = load_embedder()
    reranker = load_reranker()

    assert embedder is not None, "Embedding model should be loaded from local path"
    assert reranker is not None, "Reranker model should be loaded from local path"

    # Basic functionality checks
    embedder_model = cast(SentenceTransformer, embedder)
    embedding = embedder_model.encode("Smoke test sentence")
    assert embedding.shape == (384,), f"Expected embedding shape (384,), got {embedding.shape}"

    scores = cast(Any, reranker).predict([["what is AI?", "AI is a field of CS."], ["what is AI?", "The sky is blue."]])
    assert len(scores) == 2, "Reranker should return scores for both pairs"
