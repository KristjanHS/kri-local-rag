from __future__ import annotations

from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

import weaviate

from config import COLLECTION_NAME, DEFAULT_HYBRID_ALPHA, WEAVIATE_URL, get_logger
from weaviate.exceptions import WeaviateQueryError

# For manual vectorization
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:
    SentenceTransformer = None  # type: ignore

# Cache the embedding model instance after first load
_embedding_model: "SentenceTransformer | None" = None

# Set up logging for this module
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Retriever helpers
# ---------------------------------------------------------------------------


def _get_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """Return a (cached) SentenceTransformer instance for manual vectorization.

    Uses the same model as specified in ingest_pdf.py to ensure consistency.
    """
    global _embedding_model
    if SentenceTransformer is None:
        return None
    if _embedding_model is None:
        try:
            # Use the same model as ingestion to ensure vector compatibility
            _embedding_model = SentenceTransformer(model_name)
            logger.debug("Loaded embedding model: %s", model_name)
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", e)
            _embedding_model = None
    return _embedding_model


def _apply_metadata_filter(query: Any, metadata_filter: Optional[Dict[str, Any]]):
    """Apply a Weaviate `where` filter if *metadata_filter* is provided.

    The filter dict should follow Weaviate's GraphQL-like structure, e.g.::

        {"path": ["source"], "operator": "Equal", "valueText": "manual"}
    """
    if metadata_filter:
        return query.filter(metadata_filter)
    return query


def get_top_k(
    question: str,
    k: int = 5,
    *,
    metadata_filter: Optional[Dict[str, Any]] = None,
    alpha: float = DEFAULT_HYBRID_ALPHA,  # 0 → pure BM25 search, 1 → pure vector search
) -> List[str]:
    """Return the *content* strings of the **k** chunks most relevant to *question*.

    Improvements over the old implementation:
    1. **Hybrid search** – combines BM25 lexical matching with vector similarity.
    2. Optional **metadata filtering** via the *metadata_filter* parameter.
    3. Automatic **fallback** to *near_text* if hybrid search is not available
       (e.g. older Weaviate versions without the hybrid module).
    """

    parsed_url = urlparse(WEAVIATE_URL)
    client = weaviate.connect_to_custom(
        http_host=parsed_url.hostname,
        http_port=parsed_url.port or 80,
        grpc_host=parsed_url.hostname,
        grpc_port=50051,
        http_secure=parsed_url.scheme == "https",
        grpc_secure=parsed_url.scheme == "https",
    )
    try:
        collection = client.collections.get(COLLECTION_NAME)

        q = collection.query
        q = _apply_metadata_filter(q, metadata_filter)

        try:
            # For manual vectorization, we need to provide the vector ourselves
            embedding_model = _get_embedding_model()
            if embedding_model is not None:
                # Vectorize the query using the same model as ingestion
                query_vector = embedding_model.encode(question)
                # Hybrid search with manually provided vector
                res = q.hybrid(vector=query_vector, query=question, alpha=alpha, limit=k)
                logger.info("hybrid search used with manual vectorization (alpha=%s)", alpha)
            else:
                # Fallback: try hybrid search without manual vectorization (legacy behavior)
                # This might fail if no vectorizer is configured
                res = q.hybrid(query=question, alpha=alpha, limit=k)
                logger.info("hybrid search used (alpha=%s)", alpha)
        except (TypeError, WeaviateQueryError) as e:
            # Possible causes: old client without hybrid, empty collection error, vectorizer missing, etc.
            logger.info("hybrid failed (%s); falling back to bm25", e)
            try:
                res = q.bm25(query=question, limit=k)
            except Exception:
                # If even BM25 fails (e.g., collection truly empty), return empty list
                return []

        logger.info("Found %d candidates.", len(res.objects))

        # Weaviate returns objects already ordered by relevance. If a distance
        # attribute is present we sort on it just in case.
        objects = res.objects
        if objects and hasattr(objects[0], "distance"):
            objects.sort(key=lambda o: getattr(o, "distance", 0.0))

        # Extract content and add detailed debug logging
        chunks = []
        for i, obj in enumerate(objects):
            content = str(obj.properties.get("content", ""))
            chunks.append(content)

            # Log detailed chunk information
            distance = getattr(obj, "distance", "N/A")
            score = getattr(obj, "score", "N/A")
            logger.debug("Chunk %d:", i + 1)
            logger.debug("  Distance: %s", distance)
            logger.debug("  Score: %s", score)
            logger.debug(
                "  Content: %s",
                content[:200] + "..." if len(content) > 200 else content,
            )
            logger.debug("  Content length: %d characters", len(content))

        return chunks
    finally:
        client.close()
