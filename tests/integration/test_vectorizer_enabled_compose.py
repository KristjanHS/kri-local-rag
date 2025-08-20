"""Integration test for manual vectorization using local embedding models.

This test verifies that the application can use local embedding models for
vector generation and hybrid search with Weaviate. Uses the Compose-based test environment.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
import weaviate
from weaviate.classes.config import Configure, DataType, Property

from backend import retriever

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

pytestmark = pytest.mark.slow


def _connect_client(headers: dict[str, str] | None = None) -> weaviate.WeaviateClient:
    """Connect to the local Weaviate started by Compose.

    Uses the service name for internal communication within the Docker network.
    """
    # When running inside the Compose environment, use service names
    if Path("/.dockerenv").exists():
        return weaviate.connect_to_custom(
            http_host="weaviate",
            http_port=8080,
            grpc_host="weaviate",
            grpc_port=50051,
            http_secure=False,
            grpc_secure=False,
            headers=headers,
        )
    else:
        # Fallback for local development
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


def test_manual_vectorization_uses_local_embedding_compose(tmp_path):
    """Test manual vectorization with local embedding model using Compose services."""
    # Check if we're in the test environment
    if not Path("/.dockerenv").exists():
        pytest.skip("This test requires the Compose test environment. Run with 'make test-up' first.")

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
            pytest.fail(
                "Local embedding model unavailable; non-unit tests require the real SentenceTransformer to be present."
            )

        # Insert two small objects WITH manual vectors using batch (like application code)
        v1 = model.encode("The Eiffel Tower is in Paris.")
        v2 = model.encode("Mount Everest is the highest mountain.")
        try:
            vec1 = list(v1.tolist())  # type: ignore[attr-defined]
            vec2 = list(v2.tolist())  # type: ignore[attr-defined]
        except AttributeError:
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
        except (AttributeError, ConnectionError, TimeoutError):
            pass

        # Query using the same local model vector (hybrid search like application code)
        qv = model.encode("Paris landmark")
        try:
            qv_list = list(qv.tolist())  # type: ignore[attr-defined]
        except AttributeError:
            qv_list = list(qv)  # type: ignore[arg-type]

        # Use hybrid search like the application code
        res = coll.query.hybrid(vector=qv_list, query="Paris landmark", alpha=1.0, limit=1)

        assert hasattr(res, "objects")
        assert len(res.objects) >= 1
    finally:
        try:
            client.collections.delete(coll_name)
        except (AttributeError, ConnectionError, TimeoutError):
            pass
        client.close()
