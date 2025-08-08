"""Test support helpers for ingestion.

These helpers are imported and re-exported by ``backend.ingest`` so that tests
can continue to patch via ``patch('backend.ingest.<name>')``.

Production code SHOULD NOT import from this module directly.
"""

from __future__ import annotations

from typing import List, Optional

import weaviate
from langchain.docstore.document import Document
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
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


def ingest_documents(
    *,
    collection_name: str,
    data_path: str,
    weaviate_client,  # Accept Any to support MagicMock in tests
) -> None:
    """TEST-ONLY: Simplified ingestion used by integration tests.

    Loads Markdown files, obtains vectors via ``get_embedding_model`` and performs
    a single batch insert using ``collection.data.insert_many``.
    """
    loader = DirectoryLoader(
        data_path,
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        show_progress=False,
        use_multithreading=False,
    )
    docs: List[Document] = loader.load()
    if not docs:
        logger.warning(f"No documents found in '{data_path}'.")
        return

    # IMPORTANT: Call through backend.ingest so tests that patch
    # patch("backend.ingest.get_embedding_model") affect this call site.
    from backend import ingest as ingest_mod  # local import to avoid cycles at import time

    model = ingest_mod.get_embedding_model()
    if model is None:
        raise ValueError("Embedding model not available")

    # Ensure collection exists (tests expect 'create' to be invoked)
    _ = weaviate_client.collections.create(  # type: ignore[attr-defined]
        name=collection_name,
        vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
    )

    # In some tests, the provided object is a mocked collection._client; prefer the
    # parent mock so that assertions on collection.data.insert_many are observed.
    if hasattr(weaviate_client, "_mock_parent") and hasattr(weaviate_client._mock_parent, "data"):
        collection = weaviate_client._mock_parent
    else:
        collection = weaviate_client.collections.create.return_value

    objects: list[dict] = []
    for doc in docs:
        vector = model.encode(doc.page_content)
        objects.append({"content": doc.page_content, "vector": vector})

    collection.data.insert_many(objects)
