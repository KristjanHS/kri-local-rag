"""Test support helpers for ingestion.

These helpers are imported and re-exported by ``backend.ingest`` so that tests
can continue to patch via ``patch('backend.ingest.<name>')``.

Production code SHOULD NOT import from this module directly.
"""

from __future__ import annotations

from typing import Optional

from sentence_transformers import SentenceTransformer

from backend.config import EMBEDDING_MODEL, get_logger

logger = get_logger(__name__)


def get_embedding_model() -> Optional[SentenceTransformer]:
    """TEST-ONLY: Return an embedding model or ``None`` if unavailable.

    Tests patch this helper to avoid heavy model loading and to control outputs.
    """
    try:
        return SentenceTransformer(EMBEDDING_MODEL)
    except Exception:
        return None
