#!/usr/bin/env python3
"""Environment test to verify real CrossEncoder is loaded and used for reranking.

Marks: slow, environment
"""

import importlib
import os
import sys

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.environment]


def test_cross_encoder_is_loaded_and_used_for_reranking():
    # Require sentence_transformers; skip if not installed
    pytest.importorskip("sentence_transformers")

    # Ensure heavy compile optimizations are disabled for speed in tests
    os.environ["RERANKER_CROSS_ENCODER_OPTIMIZATIONS"] = "false"

    # Make sure sentence_transformers is actually imported and present in sys.modules
    import sentence_transformers as _st  # noqa: F401

    # Reload qa_loop with sentence_transformers present so its snapshot allows loading
    if "backend.qa_loop" in sys.modules:
        del sys.modules["backend.qa_loop"]
    qa_loop = importlib.import_module("backend.qa_loop")

    # Reset cached encoder
    qa_loop._cross_encoder = None  # type: ignore[attr-defined]

    # Load the encoder (real CrossEncoder should be returned)
    encoder = qa_loop._get_cross_encoder()
    assert encoder is not None, "Expected real CrossEncoder to be loaded"
    assert hasattr(encoder, "predict"), "CrossEncoder should expose a predict method"

    # Wrap predict to count invocations while still calling the real implementation
    call_count = {"n": 0}
    real_predict = encoder.predict

    def _wrapped_predict(pairs):  # type: ignore[no-redef]
        call_count["n"] += 1
        return real_predict(pairs)

    # Monkey-patch the cached instance. _score_chunks will reuse the cached encoder.
    encoder.predict = _wrapped_predict  # type: ignore[assignment]

    # Drive scoring on two chunks
    question = "What is retrieval augmented generation?"
    chunks = [
        "Retrieval Augmented Generation (RAG) combines document retrieval with generation.",
        "Completely unrelated content about cooking recipes.",
    ]

    scored = qa_loop._score_chunks(question, chunks)
    assert len(scored) == 2
    assert all(hasattr(sc, "score") for sc in scored)
    # Ensure CrossEncoder.predict was actually called
    assert call_count["n"] == 1, "Expected CrossEncoder.predict to be used for scoring"
