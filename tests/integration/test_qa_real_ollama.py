"""Integration test that hits the real Ollama model while bypassing Weaviate.

This test exercises the QA path end-to-end with the actual LLM by patching only
the retrieval step.
"""

from unittest.mock import patch

import pytest

from backend.config import OLLAMA_MODEL
from backend.ollama_client import ensure_model_available
from backend.qa_loop import answer

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.external]


@patch("backend.qa_loop.get_top_k", return_value=["Paris is the capital of France."])
def test_answer_uses_real_ollama(_mock_get_top_k, docker_services):
    # Ensure the required model is available (will download with visible progress if missing)
    assert ensure_model_available(OLLAMA_MODEL) is True
    question = "What is the capital of France?"
    # Use a small k to keep the prompt minimal; actual generation length is controlled by server/model
    out = answer(question, k=1)
    assert isinstance(out, str) and out.strip(), "Expected a non-empty answer from the real model"
