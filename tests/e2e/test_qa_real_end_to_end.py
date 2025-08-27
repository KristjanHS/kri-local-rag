"""E2E QA path test that hits real Weaviate and the real Ollama model.

It relies on pytest-docker's services being available and the helper fixture
to verify/populate Weaviate with example data.
"""

import importlib
import os
import sys

import pytest

pytest_plugins = ["tests.e2e.fixtures_ingestion"]
from backend.config import OLLAMA_MODEL
from backend.ollama_client import pull_if_missing
from backend.qa_loop import answer
from tests.conftest import TEST_COLLECTION_NAME

pytestmark = [pytest.mark.slow, pytest.mark.external]


@pytest.mark.external
def test_e2e_answer_with_real_services(
    docker_services_ready, cross_encoder_cache_dir, weaviate_client, sample_documents_path
):  # noqa: ANN001
    """
    Asks a generic question; retrieval should find some context from example_data
    and the LLM should provide a coherent answer based on it.
    """
    # Ensure the required model is available (single pull request if missing)
    assert pull_if_missing(OLLAMA_MODEL) is True
    # Ensure fake-answer mode is not active
    if "RAG_FAKE_ANSWER" in os.environ:
        del os.environ["RAG_FAKE_ANSWER"]

    # Set up CrossEncoder environment like integration tests
    os.environ["RERANKER_CROSS_ENCODER_OPTIMIZATIONS"] = "false"
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = cross_encoder_cache_dir

    # Reload qa_loop to ensure it picks up the changed environment variables
    if "backend.qa_loop" in sys.modules:
        importlib.reload(sys.modules["backend.qa_loop"])
    qa_loop = importlib.import_module("backend.qa_loop")

    # Explicitly load the CrossEncoder to ensure it's available
    cross_encoder = qa_loop._get_cross_encoder()
    assert cross_encoder is not None, "Expected CrossEncoder to be loaded from cache"

    # Clean up any existing collection before test
    try:
        if weaviate_client.collections.exists(TEST_COLLECTION_NAME):
            weaviate_client.collections.delete(TEST_COLLECTION_NAME)
    except Exception:
        pass  # Ignore cleanup errors

    # Ensure TestCollection has data by ingesting sample documents
    from backend import ingest
    from backend.retriever import _get_embedding_model

    embedding_model = _get_embedding_model()
    ingest.ingest(
        directory=sample_documents_path,
        collection_name=TEST_COLLECTION_NAME,
        weaviate_client=weaviate_client,
        embedding_model=embedding_model,
    )

    # Ask a generic question; retrieval should find some context from example_data
    # Note: answer() function will get its own client, so no need for fresh client here
    result = answer(
        "Give me a brief summary of the indexed content.",
        k=2,
        collection_name=TEST_COLLECTION_NAME,
        cross_encoder=cross_encoder,
    )

    assert isinstance(result, str) and result.strip(), "Expected non-empty model output"
    assert "I found no relevant context" not in result, "Expected retrieval to provide context from Weaviate"

    # Clean up collection after test
    try:
        if weaviate_client.collections.exists(TEST_COLLECTION_NAME):
            weaviate_client.collections.delete(TEST_COLLECTION_NAME)
    except Exception:
        pass  # Ignore cleanup errors
