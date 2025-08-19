"""Integration test that hits the real Ollama model while bypassing Weaviate.

This test exercises the QA path end-to-end with the actual LLM by patching only
the retrieval step. Uses the Compose-based test environment.
"""

from pathlib import Path

import pytest

from backend.config import OLLAMA_MODEL
from backend.ollama_client import ensure_model_available
from backend.qa_loop import answer


def test_answer_uses_real_ollama_compose(managed_get_top_k):
    """Test QA with real Ollama using Compose services."""
    # Check if we're in the test environment
    if not Path("/.dockerenv").exists():
        pytest.skip("This test requires the Compose test environment. Run with 'make test-up' first.")

    # Configure the mock provided by the fixture
    managed_get_top_k.return_value = ["Paris is the capital of France."]

    # Ensure the required model is available (will download with visible progress if missing)
    assert ensure_model_available(OLLAMA_MODEL) is True
    question = "What is the capital of France?"
    # Use a small k to keep the prompt minimal; actual generation length is controlled by server/model
    from backend.qa_loop import _get_cross_encoder

    cross_encoder = _get_cross_encoder()
    out = answer(question, k=1, cross_encoder=cross_encoder)
    assert isinstance(out, str) and out.strip(), "Expected a non-empty answer from the real model"


# Test comment
