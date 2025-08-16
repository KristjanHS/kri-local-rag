#!/usr/bin/env python3
"""Environment test to verify real CrossEncoder is loaded and used for reranking.

Marks: slow
"""

import importlib
import os
import sys

import pytest

pytestmark = [pytest.mark.slow]


def test_cross_encoder_is_loaded_and_used_for_reranking(cross_encoder_cache_dir):
    """Verify that the real CrossEncoder is loaded from the local cache and used for reranking."""
    # Ensure heavy compile optimizations are disabled for speed in tests
    os.environ["RERANKER_CROSS_ENCODER_OPTIMIZATIONS"] = "false"
    # Point to the local cache for offline loading
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cross_encoder_cache_dir

    # Reload qa_loop to ensure it picks up the changed environment variables
    if "backend.qa_loop" in sys.modules:
        importlib.reload(sys.modules["backend.qa_loop"])
    qa_loop = importlib.import_module("backend.qa_loop")

    # Reset cached encoder to ensure a fresh load
    qa_loop._cross_encoder = None  # type: ignore[reportAttributeAccessIssue]

    # Load the encoder (real CrossEncoder should be returned)
    encoder = qa_loop._get_cross_encoder()
    assert encoder is not None, "Expected real CrossEncoder to be loaded from cache"

    # Drive scoring on two chunks
    question = "What is retrieval augmented generation?"
    chunks = [
        "Retrieval Augmented Generation (RAG) combines document retrieval with generation.",
        "Completely unrelated content about cooking recipes.",
    ]

    scored = qa_loop._score_chunks(question, chunks)
    assert len(scored) == 2
    assert all(hasattr(sc, "score") for sc in scored)

    # Verify that the scores are realistic and not fallback values (e.g., 0.0 or keyword-based)
    # A relevant chunk should have a significantly higher score than an irrelevant one.
    assert scored[0].score > scored[1].score, "Expected relevant chunk to have a higher score"
    assert scored[1].score < 0.1, "Expected irrelevant chunk to have a very low score"
