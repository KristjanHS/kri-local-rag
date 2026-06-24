from __future__ import annotations

from typing import Any, List, Optional

# Defer torch import to runtime to avoid heavy import-time side effects
from weaviate.exceptions import WeaviateQueryError

from backend.config import (
    COLLECTION_NAME,
    DEFAULT_HYBRID_ALPHA,
    get_logger,
)
from backend.models import load_embedder
from backend.vector_utils import to_float_list
from backend.weaviate_client import get_weaviate_client

# Set up logging for this module
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Retriever helpers
# ---------------------------------------------------------------------------


def get_top_k(
    question: str,
    k: int = 5,
    *,
    alpha: float = DEFAULT_HYBRID_ALPHA,  # 0 → pure BM25 search, 1 → pure vector search
    embedding_model: Optional[Any] = None,
    collection_name: Optional[str] = None,
) -> List[str]:
    """Return the *content* strings of the **k** chunks most relevant to *question*.

    Uses **hybrid search** – BM25 lexical matching combined with vector similarity
    from a query vector produced by the local embedding model.
    """

    # Get Weaviate client - note: client is cached and should be closed at application level
    client = get_weaviate_client()
    # Use provided collection_name or fall back to default
    target_collection = collection_name or COLLECTION_NAME
    collection = client.collections.get(target_collection)

    q = collection.query
    try:
        # For manual vectorization, we need to provide the vector ourselves.
        # load_embedder() is the single cache owner; it raises on failure (never None).
        if embedding_model is None:
            embedding_model = load_embedder()

        # Vectorize the query using the same model as ingestion
        query_vector_raw = embedding_model.encode(question)
        # Normalize to a plain Python list of floats for Weaviate client
        query_vector: List[float] = to_float_list(query_vector_raw)
        # Hybrid search with manually provided vector
        res = q.hybrid(vector=query_vector, query=question, alpha=alpha, limit=k)
        logger.info("hybrid search used with manual vectorization (alpha=%s)", alpha)
    except (TypeError, WeaviateQueryError) as e:
        # Hybrid search failed - this should not happen in tests with proper setup
        logger.error("hybrid search failed (%s)", e)
        raise RuntimeError(f"Hybrid search failed: {e}") from e

    logger.info("Found %d candidates.", len(res.objects))

    # Weaviate returns objects already ordered by hybrid relevance.
    objects: list[Any] = list(res.objects)

    # Extract content and show chunk heads at INFO level
    chunks: list[str] = []
    for i, obj in enumerate(objects):
        content = str(obj.properties.get("content", ""))
        chunks.append(content)

        # Show the head of each chunk at INFO level
        head = content[:100].replace("\n", " ").replace("\r", " ").strip()
        if len(content) > 100:
            head += "..."
        logger.info("Chunk %d: %s", i + 1, head)

        # Keep detailed debug logging for when needed
        distance = getattr(obj, "distance", "N/A")
        score = getattr(obj, "score", "N/A")
        logger.debug("  Distance: %s", distance)
        logger.debug("  Score: %s", score)
        logger.debug("  Content length: %d characters", len(content))

    return chunks
