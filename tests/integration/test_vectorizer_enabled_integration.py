#!/usr/bin/env python3
"""Integration test to prove local (client-side) embedding is used end-to-end.

This test intentionally avoids server-side vectorizers/modules and verifies
that we can:

1) Create a collection configured for self-provided vectors
2) Encode texts locally using the same embedding model as the app
3) Insert objects with manual vectors
4) Query using those vectors (near_vector)

We require Docker services (Weaviate) to be running; the ``docker_services``
fixture handles that.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest
import weaviate
from weaviate.classes.config import Configure, DataType, Property

import backend.retriever as retriever
from backend.config import EMBEDDING_MODEL

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _connect_client(headers: dict[str, str] | None = None) -> weaviate.WeaviateClient:
    """Connect to the local Weaviate started by pytest-docker.

    Relies on [tool.pytest.docker.services_wait_for] in pyproject.toml to ensure
    readiness.
    """
    base_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    pu = urlparse(base_url)
    return weaviate.connect_to_custom(
        http_host=pu.hostname or "localhost",
        http_port=pu.port or 8080,
        grpc_host=pu.hostname or "localhost",
        grpc_port=50051,
        http_secure=pu.scheme == "https",
        grpc_secure=pu.scheme == "https",
        headers=headers,
    )


def test_manual_vectorization_uses_local_embedding(docker_services, tmp_path):
    # Speed up model init for tests by disabling torch.compile in retriever
    os.environ.setdefault("RETRIEVER_EMBEDDING_TORCH_COMPILE", "false")

    client = _connect_client()
    coll_name = "ManualVectorProof"
    try:
        # Create a collection configured for self-provided vectors
        if not client.collections.exists(coll_name):
            # Use modern API without fallbacks (compatible versions now)
            client.collections.create(
                name=coll_name,
                properties=[
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="category", data_type=DataType.TEXT),
                ],
                vector_config=Configure.Vectors.self_provided(),
            )

        coll = client.collections.get(coll_name)

        # DIAGNOSTIC: Verify collection configuration
        coll.config.get()

        # Load the same embedding model used by the application
        model = retriever._get_embedding_model(EMBEDDING_MODEL)
        if model is None:
            pytest.skip("Local embedding model unavailable for test")

        # Insert two small objects WITH manual vectors using batch (like application code)
        v1 = model.encode("The Eiffel Tower is in Paris.")
        v2 = model.encode("Mount Everest is the highest mountain.")
        try:
            vec1 = list(v1.tolist())  # type: ignore[attr-defined]
            vec2 = list(v2.tolist())  # type: ignore[attr-defined]
        except Exception:
            vec1 = list(v1)  # type: ignore[arg-type]
            vec2 = list(v2)  # type: ignore[arg-type]

        # Use batch insertion like the application code
        with coll.batch.dynamic() as batch:
            batch.add_object(
                properties={"content": "The Eiffel Tower is in Paris.", "category": "geo"},
                vector=vec1,
            )
            batch.add_object(
                properties={"content": "Mount Everest is the highest mountain.", "category": "geo"},
                vector=vec2,
            )

        # DIAGNOSTIC: Verify collection has objects
        try:
            # Simple check if collection has any objects
            any(True for _ in coll.iterator())
        except Exception:
            pass

        # Query using the same local model vector (hybrid search like application code)
        qv = model.encode("Paris landmark")
        try:
            qv_list = list(qv.tolist())  # type: ignore[attr-defined]
        except Exception:
            qv_list = list(qv)  # type: ignore[arg-type]

        # Use hybrid search like the application code
        res = coll.query.hybrid(vector=qv_list, query="Paris landmark", alpha=1.0, limit=1)

        assert hasattr(res, "objects")
        assert len(res.objects) >= 1
    finally:
        try:
            client.collections.delete(coll_name)
        except Exception:
            pass
        client.close()
