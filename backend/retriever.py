from __future__ import annotations

from typing import List, Optional, Dict, Any

import weaviate
import os

from config import COLLECTION_NAME, DEFAULT_HYBRID_ALPHA

# ---------------------------------------------------------------------------
# Retriever helpers
# ---------------------------------------------------------------------------


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
    debug: bool = False,
) -> List[str]:
    """Return the *content* strings of the **k** chunks most relevant to *question*.

    Improvements over the old implementation:
    1. **Hybrid search** – combines BM25 lexical matching with vector similarity.
    2. Optional **metadata filtering** via the *metadata_filter* parameter.
    3. Automatic **fallback** to *near_text* if hybrid search is not available
       (e.g. older Weaviate versions without the hybrid module).
    """

    url = os.getenv("WEAVIATE_URL")
    client = weaviate.Client(url=url) if url else weaviate.connect_to_local()  # type: ignore[attr-defined]
    try:
        docs = client.collections.get(COLLECTION_NAME)  # type: ignore[attr-defined]

        q = docs.query
        q = _apply_metadata_filter(q, metadata_filter)

        try:
            # Preferred: hybrid lexical + semantic search in a single call.
            res = q.hybrid(query=question, alpha=alpha, limit=k)
            if debug:
                print(f"[Debug][Retriever] hybrid search used (alpha={alpha})")
        except AttributeError:
            # Fallback for older clients/servers – use near_text.
            res = q.near_text(query=question, limit=k)
            if debug:
                print("[Debug][Retriever] hybrid not available – falling back to near_text")

        # Weaviate returns objects already ordered by relevance. If a distance
        # attribute is present we sort on it just in case.
        objects = res.objects
        if objects and hasattr(objects[0], "distance"):
            objects.sort(key=lambda o: getattr(o, "distance", 0.0))

        return [str(o.properties.get("content", "")) for o in objects]
    finally:
        client.close()  # type: ignore[attr-defined]
