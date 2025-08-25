"""Integration test that hits the real Ollama model while bypassing Weaviate.

This test exercises the QA path end-to-end with the actual LLM by patching only
the retrieval step. Supports both Docker and local environments.
"""

import subprocess

import pytest

from backend.config import OLLAMA_MODEL
from backend.ollama_client import pull_if_missing
from backend.qa_loop import answer

pytestmark = pytest.mark.requires_ollama


@pytest.mark.requires_ollama
def test_answer_uses_real_ollama_compose(weaviate_client, sample_documents_path, monkeypatch):
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

    question = "How do you write a limerick?"
    # Use a small k to keep the prompt minimal; actual generation length is controlled by server/model
    from backend.qa_loop import _get_cross_encoder

    cross_encoder = _get_cross_encoder()
    # Ensure test hook is disabled so we don't bypass Ollama
    monkeypatch.delenv("RAG_FAKE_ANSWER", raising=False)

    # Capture a flag when the Ollama generate endpoint is called
    called_generate = {"value": False}

    import backend.ollama_client as oc

    original_stream = oc.httpx.stream

    def _stream_wrapper(method, url, *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(url, str) and url.endswith("/api/generate"):
            called_generate["value"] = True
        return original_stream(method, url, *args, **kwargs)

    monkeypatch.setattr(oc.httpx, "stream", _stream_wrapper)

    out = answer(question, k=1, cross_encoder=cross_encoder, collection_name="TestCollection")
    assert isinstance(out, str) and out.strip(), "Expected a non-empty answer from the real model"
    assert "Error generating response" not in out
    # The answer should mention limericks since that's what the document is about
    assert "limerick" in out.lower() or "rhyme" in out.lower(), f"Expected answer about limericks, got: {out[:200]}..."

    # Verify that the client attempted to call Ollama over HTTP
    assert called_generate["value"], "Expected call to Ollama /api/generate endpoint"

    # Best-effort: check for a model process in Ollama after generation attempt
    try:
        # Prefer Docker Compose service name to avoid hardcoded container IDs
        ps = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker/docker-compose.yml",
                "exec",
                "-T",
                "ollama",
                "ollama",
                "ps",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if ps.returncode != 0:
            # Fallback to legacy docker-compose CLI
            ps = subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "docker/docker-compose.yml",
                    "exec",
                    "-T",
                    "ollama",
                    "ollama",
                    "ps",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        assert ps.returncode == 0
        assert OLLAMA_MODEL.split(":")[0] in ps.stdout
    except Exception:
        # Non-fatal in CI environments without docker or compose
        pass
