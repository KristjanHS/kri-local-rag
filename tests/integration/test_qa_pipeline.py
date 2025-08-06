#!/usr/bin/env python3
"""Integration tests for the QA pipeline."""

import os

import pytest
from langchain.docstore.document import Document
from sentence_transformers import SentenceTransformer
from testcontainers.core.container import DockerContainer
from testcontainers.weaviate import WeaviateContainer

from backend.config import EMBEDDING_MODEL, OLLAMA_MODEL
from backend.ingest import process_and_upload_chunks


class OllamaContainer(DockerContainer):
    def __init__(self, image="ollama/ollama:latest", **kwargs):
        super().__init__(image, **kwargs)
        self.with_exposed_ports(11434)

    def start(self):
        super().start()
        # It's important to wait for the container to be ready before pulling the model.
        self.wait_for_logs("Listening on", timeout=20)
        self.pull_model()
        return self

    def pull_model(self, model_name=OLLAMA_MODEL):
        exit_code, output = self.exec(f"ollama pull {model_name}")
        if exit_code != 0:
            raise RuntimeError(f"Failed to pull model {model_name}: {output.decode()}")

    def get_url(self):
        return f"http://{self.get_container_host_ip()}:{self.get_port(11434)}"


@pytest.mark.integration
@pytest.mark.slow
def test_qa_pipeline(monkeypatch):
    """Test the full QA pipeline with real Weaviate and Ollama instances."""
    with WeaviateContainer() as weaviate_container, OllamaContainer() as ollama_container:
        weaviate_client = weaviate_container.get_client()
        ollama_url = ollama_container.get_url()

        # monkeypatch the environment variables to use the container URLs
        monkeypatch.setenv("WEAVIATE_URL", weaviate_container.get_url())
        monkeypatch.setenv("OLLAMA_URL", ollama_url)

        # Ingest some data
        docs = [Document(page_content="This is a test document about painting.", metadata={"source": "test.txt"})]
        model = SentenceTransformer(EMBEDDING_MODEL)
        process_and_upload_chunks(weaviate_client, docs, model)

        # Run the QA loop
        question = "What is this document about?"
        # This is a bit of a hack to run the qa_loop, which is a __main__ script.
        # We can't import and run it directly, so we'll run it as a subprocess.
        # A better solution would be to refactor qa_loop.py to be more modular.
        import subprocess

        env = {
            **os.environ,
            "WEAVIATE_URL": weaviate_container.get_url(),
            "OLLAMA_URL": ollama_url,
        }
        result = subprocess.run(
            [
                "python",
                "-m",
                "backend.qa_loop",
                "--question",
                question,
                "--num-chunks",
                "1",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert "painting" in result.stdout.lower()
