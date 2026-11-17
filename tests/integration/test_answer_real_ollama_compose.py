"""Integration test: ingest the example fixture, then answer with the real Ollama model.

Ingests ``example_data/`` (a small self-authored PDF about a fictional lighthouse)
into the compose Weaviate, asks a question only that document answers, and checks
the real LLM was called over HTTP and grounded its answer in the retrieved chunk.
Supports both Docker and local environments.
"""

import subprocess

import pytest

from backend.config import OLLAMA_MODEL
from backend.ollama_client import pull_if_missing
from backend.qa_loop import answer
from tests.conftest import TEST_COLLECTION_NAME

pytestmark = pytest.mark.requires_ollama

# Fact stated only in example_data/juniper_point_lighthouse.pdf.
QUESTION = "What colour was the Juniper Point lighthouse lamp room repainted in 1987?"
EXPECTED_TERM = "teal"


@pytest.mark.requires_ollama
def test_answer_grounded_in_example_fixture_with_real_ollama(
    weaviate_client, test_collection_name, sample_documents_path, monkeypatch
):
    """Ingest the example fixture, then answer from it with the real Ollama model."""
    from backend import ingest
    from backend.models import load_embedder

    embedding_model = load_embedder()
    ingest.ingest(
        source=sample_documents_path,
        collection_name=TEST_COLLECTION_NAME,
        weaviate_client=weaviate_client,
        embedding_model=embedding_model,
    )

    # Ensure the required model is available (single pull request if missing)
    assert pull_if_missing(OLLAMA_MODEL) is True

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

    # Small k keeps the prompt minimal; the fixture is a single chunk.
    out = answer(QUESTION, k=1, cross_encoder=cross_encoder, collection_name=TEST_COLLECTION_NAME)
    assert isinstance(out, str) and out.strip(), "Expected a non-empty answer from the real model"
    assert "Error generating response" not in out
    assert EXPECTED_TERM in out.lower(), f"Expected an answer grounded in the fixture, got: {out[:200]}..."

    # Verify that the client attempted to call Ollama over HTTP
    assert called_generate["value"], "Expected call to Ollama /api/generate endpoint"

    # Best-effort: check for a model process in Ollama after generation attempt
    try:
        # Prefer Docker Compose service name to avoid hardcoded container IDs
        base_cmd = [
            "-f",
            "docker/docker-compose.yml",
            "exec",
            "-T",
            "ollama",
            "ollama",
            "ps",
        ]
        run_kwargs = {"capture_output": True, "text": True, "timeout": 10}

        # Try with Docker Compose v2 ("docker compose")
        ps = subprocess.run(["docker", "compose"] + base_cmd, **run_kwargs)

        # Fallback to legacy docker-compose CLI if v2 invocation fails
        if ps.returncode != 0:
            ps = subprocess.run(["docker-compose"] + base_cmd, **run_kwargs)
        assert ps.returncode == 0
        assert OLLAMA_MODEL.split(":")[0] in ps.stdout
    except Exception:
        # Non-fatal in CI environments without docker or compose
        pass
