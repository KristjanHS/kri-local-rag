#!/usr/bin/env python3
"""Document Ingestion Script

This script uses LangChain for robust document loading and a manual pipeline
for vectorization and storage to offer detailed control.

Usage:
    python backend/ingest.py --data-dir ./data

Key Features:
-   **Multi-Format Support**: Ingests PDF and Markdown files via LangChain loaders.
-   **Manual Control**: Provides explicit control over sentence transformation and Weaviate upsert logic.
-   **Idempotent**: Re-running the script updates existing documents without creating duplicates.
-   **CPU Optimized**: Leverages a CPU-optimized sentence-transformer model.
"""

import argparse
import hashlib
import os
import time
from datetime import datetime, timezone
from typing import List, Optional, cast

import torch
import weaviate
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, UnstructuredMarkdownLoader
from sentence_transformers import SentenceTransformer

from backend.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    WEAVIATE_BATCH_SIZE,
    WEAVIATE_CONCURRENT_REQUESTS,
    WEAVIATE_URL,
    get_logger,
)
from backend.vector_utils import to_float_list

# --- Logging Setup ---
logger = get_logger(__name__)


def load_and_split_documents(path: str) -> List[Document]:
    """Load documents from a directory or a single file, then split into chunks."""
    # Fast path: if the path does not exist, skip gracefully
    if not os.path.exists(path):
        logger.warning(f"Path not found: '{path}'. Skipping ingestion.")
        return []
    # Choose the most robust/accurate PDF loader available in this environment
    pdf_loader_cls = PyPDFLoader
    try:
        from langchain_community.document_loaders import PyMuPDFLoader  # type: ignore

        pdf_loader_cls = PyMuPDFLoader  # fastest, robust on malformed PDFs
        logger.info("Using PyMuPDFLoader for PDFs (best available).")
    except Exception:
        try:
            from langchain_community.document_loaders import UnstructuredPDFLoader  # type: ignore

            pdf_loader_cls = UnstructuredPDFLoader  # layout-aware; robust
            logger.info("Using UnstructuredPDFLoader for PDFs.")
        except Exception:
            logger.info("Using PyPDFLoader for PDFs (fallback).")

    # 1) Single file path support
    docs: List[Document] = []
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            loader = pdf_loader_cls(path)
            docs.extend(loader.load())
        elif ext == ".md":
            loader = UnstructuredMarkdownLoader(path)
            docs.extend(loader.load())
        else:
            logger.warning(f"Unsupported file extension '{ext}' for path '{path}'.")
            return []
    else:
        # 2) Directory path with glob patterns
        loader_configs = {
            "**/*.pdf": pdf_loader_cls,
            "**/*.md": UnstructuredMarkdownLoader,
        }
        for glob_pattern, loader_cls in loader_configs.items():
            loader = DirectoryLoader(
                path,
                glob=glob_pattern,
                loader_cls=loader_cls,
                show_progress=True,
                use_multithreading=True,
            )
            docs.extend(loader.load())

    if not docs:
        logger.warning(f"No documents found in '{path}'.")
        return []

    logger.info(f"Loaded {len(docs)} documents.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunked_docs = text_splitter.split_documents(docs)
    logger.info(f"Split documents into {len(chunked_docs)} chunks.")

    return chunked_docs


from urllib.parse import urlparse


def connect_to_weaviate() -> weaviate.WeaviateClient:
    """Connect to the Weaviate instance."""
    logger.info(f"Connecting to Weaviate at {WEAVIATE_URL}...")
    parsed_url = urlparse(WEAVIATE_URL)
    client = weaviate.connect_to_custom(
        http_host=parsed_url.hostname or "localhost",
        http_port=parsed_url.port or 80,
        grpc_host=parsed_url.hostname or "localhost",
        grpc_port=50051,
        http_secure=parsed_url.scheme == "https",
        grpc_secure=parsed_url.scheme == "https",
    )
    logger.info("Connection successful.")
    return client


def _safe_created_at(source_path: Optional[str]) -> str:
    """Return ISO timestamp from file mtime if path exists, else current UTC time."""
    try:
        if source_path and os.path.exists(source_path):
            ts = os.path.getmtime(source_path)
        else:
            raise FileNotFoundError
    except Exception:
        ts = time.time()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def deterministic_uuid(doc: Document) -> str:
    """Generate a deterministic UUID for a document chunk."""
    content_hash = hashlib.md5(doc.page_content.encode("utf-8")).hexdigest()
    source_file = os.path.basename(doc.metadata.get("source", "unknown"))
    return hashlib.md5(f"{source_file}:{content_hash}".encode("utf-8")).hexdigest()


def create_collection_if_not_exists(client: weaviate.WeaviateClient, collection_name: str):
    """Create a collection if it doesn't exist, configured for manual vectorization."""
    if not client.collections.exists(collection_name):
        client.collections.create(
            name=collection_name,
            vector_config=weaviate.classes.config.Configure.Vectors.self_provided(),
        )
        logger.info(f"→ Collection '{collection_name}' created for manual vectorization.")
    else:
        logger.info(f"→ Collection '{collection_name}' already exists.")


def process_and_upload_chunks(
    client: weaviate.WeaviateClient,
    docs: List[Document],
    model: SentenceTransformer,
    collection_name: str,
):
    """Process each document chunk and upload it to Weaviate."""
    # Access collection (standard accessor for our tests/mocks)
    collection = client.collections.get(collection_name)
    stats = {"inserts": 0, "updates": 0, "skipped": 0}
    total_chunks = len(docs)
    logger.info(f"Encoding and uploading {total_chunks} chunks… This can take a while on first run.")
    start_ts = time.time()
    last_log_ts = start_ts

    with collection.batch.fixed_size(
        batch_size=WEAVIATE_BATCH_SIZE,
        concurrent_requests=WEAVIATE_CONCURRENT_REQUESTS,
    ) as batch:
        for idx, doc in enumerate(docs, start=1):
            uuid = deterministic_uuid(doc)
            vector_tensor = model.encode(doc.page_content)
            # Normalize to a plain Python list of floats for the Weaviate client
            vector: List[float] = to_float_list(vector_tensor)

            properties = {
                "content": doc.page_content,
                "source_file": os.path.basename(doc.metadata.get("source", "unknown")),
                "source": os.path.splitext(doc.metadata.get("source", "unknown"))[1],
                # Derive created_at from source file if it exists; fall back to now.
                "created_at": _safe_created_at(doc.metadata.get("source")),
            }

            # This logic remains manual as requested, but uses batching for efficiency
            # Note: A true "check-then-update" is less efficient in batch.
            # A more common pattern is to just upsert, which Weaviate handles.
            # Here we simulate the original logic's intent within the batch context.
            batch.add_object(
                properties=properties,
                uuid=uuid,
                vector=vector,
            )
            # A full upsert logic would require checking existence first,
            # which defeats the purpose of batching. Weaviate's batching
            # with specified UUIDs effectively handles this as an upsert.
            stats["inserts"] += 1  # We'll count all as inserts for simplicity in batch mode.

            # Periodic progress logging (every ~100 chunks or 10 seconds)
            now = time.time()
            if idx == 1 or idx % 100 == 0 or (now - last_log_ts) >= 10:
                elapsed = now - start_ts
                rate = idx / elapsed if elapsed > 0 else 0.0
                remaining = max(total_chunks - idx, 0)
                eta_s = (remaining / rate) if rate > 0 else 0.0
                logger.info(
                    f"Progress: {idx}/{total_chunks} chunks ({idx / max(total_chunks, 1):.0%}), "
                    f"{rate:.1f} chunks/s, ETA ~{eta_s:.0f}s"
                )
                last_log_ts = now

    logger.info(f"Batch ingestion complete: {stats}")
    return stats


"""
Test-only hooks (re-exported for integration tests)
These are re-exported from backend._test_support so tests can patch via
backend.ingest.get_embedding_model / backend.ingest.ingest_documents
without changing their import paths.
"""
try:  # pragma: no cover - optional in production
    from backend._test_support import (  # type: ignore
        get_embedding_model as get_embedding_model,
    )
    from backend._test_support import (
        ingest_documents as ingest_documents,
    )
except Exception:  # pragma: no cover
    pass


def ingest(
    directory: str,
    collection_name: str = COLLECTION_NAME,
    *,
    embedding_model: Optional[SentenceTransformer] = None,
    client: Optional[weaviate.WeaviateClient] = None,
):
    """Main ingestion pipeline."""
    start_time = time.time()

    chunked_docs = load_and_split_documents(directory)
    if not chunked_docs:
        return

    # Resolve embedding model (allow DI for tests)
    if embedding_model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)
        try:
            logger.info("torch.compile: optimizing embedding model – this may take a minute on first run…")
            compiled_model = torch.compile(model, backend="inductor", mode="max-autotune")  # type: ignore[attr-defined]
            model = cast(SentenceTransformer, compiled_model)
            logger.info("torch.compile optimization completed.")
        except Exception as e:
            logger.warning(f"Could not apply torch.compile: {e}")
    else:
        model = embedding_model

    # Resolve client (allow DI for tests)
    created_client = False
    if client is None:
        client = connect_to_weaviate()
        created_client = True
    try:
        create_collection_if_not_exists(client, collection_name)
        process_and_upload_chunks(client, chunked_docs, model, collection_name)
    finally:
        if created_client and hasattr(client, "close"):
            client.close()

    elapsed = time.time() - start_time
    logger.info("── Summary ─────────────────────────────")
    logger.info(f"✓ {len(chunked_docs)} chunks processed and ingested.")
    logger.info(f"Elapsed: {elapsed:.1f} s")


# --- CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents (.pdf, .md) into Weaviate.")
    parser.add_argument("--data-dir", default="../data", help="Directory with document files.")
    args = parser.parse_args()
    ingest(str(args.data_dir))
