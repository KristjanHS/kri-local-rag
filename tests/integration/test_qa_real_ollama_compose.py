"""Integration test that hits the real Ollama model while bypassing Weaviate.

This test exercises the QA path end-to-end with the actual LLM by patching only
the retrieval step. Supports both Docker and local environments.
"""

import pytest

from backend.config import OLLAMA_MODEL
from backend.ollama_client import pull_if_missing
from backend.qa_loop import answer

pytestmark = pytest.mark.requires_ollama


@pytest.mark.requires_ollama
def test_answer_uses_real_ollama_compose(weaviate_client, sample_documents_path):
    """Test QA with real Ollama using both Docker and local environments."""
    # First, ensure we have data in Weaviate by running ingestion
    from backend import ingest
    from backend.retriever import _get_embedding_model

    embedding_model = _get_embedding_model()
    ingest.ingest(
        directory=sample_documents_path,
        collection_name="TestCollection",
        weaviate_client=weaviate_client,
        embedding_model=embedding_model,
    )

    # Ensure the required model is available (single pull request if missing)
    assert pull_if_missing(OLLAMA_MODEL) is True

    question = "What is the capital of France?"
    # Use a small k to keep the prompt minimal; actual generation length is controlled by server/model
    from backend.qa_loop import _get_cross_encoder

    cross_encoder = _get_cross_encoder()
    out = answer(question, k=1, cross_encoder=cross_encoder)
    assert isinstance(out, str) and out.strip(), "Expected a non-empty answer from the real model"
