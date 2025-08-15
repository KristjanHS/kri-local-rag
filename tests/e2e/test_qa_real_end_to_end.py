"""E2E QA path test that hits real Weaviate and the real Ollama model.

It relies on pytest-docker's services being available and the helper fixture
to verify/populate Weaviate with example data.
"""

import os

import pytest

pytest_plugins = ["tests.e2e.fixtures_ingestion"]
from backend.config import OLLAMA_MODEL
from backend.ollama_client import ensure_model_available
from backend.qa_loop import answer

pytestmark = [pytest.mark.e2e, pytest.mark.integration, pytest.mark.slow, pytest.mark.external]


def test_e2e_answer_with_real_services(docker_services_ready, weaviate_compose_up, ollama_compose_up):  # noqa: ANN001
    # Ensure the required model is available (will download with visible progress if missing)
    assert ensure_model_available(OLLAMA_MODEL) is True
    # Ensure fake-answer mode is not active
    if "RAG_FAKE_ANSWER" in os.environ:
        del os.environ["RAG_FAKE_ANSWER"]

    # Ask a generic question; retrieval should find some context from example_data
    result = answer("Give me a brief summary of the indexed content.", k=2)

    assert isinstance(result, str) and result.strip(), "Expected non-empty model output"
    assert "I found no relevant context" not in result, "Expected retrieval to provide context from Weaviate"
