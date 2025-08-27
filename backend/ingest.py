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
    HF_CACHE_DIR,
    WEAVIATE_BATCH_SIZE,
    WEAVIATE_CONCURRENT_REQUESTS,
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
            try:
                loader = DirectoryLoader(
                    path,
                    glob=glob_pattern,
                    loader_cls=loader_cls,
                    show_progress=True,
                    use_multithreading=True,
                )
                loaded_docs = loader.load()
                docs.extend(loaded_docs)
            except Exception as e:
                logger.error(f"Error loading documents with pattern '{glob_pattern}': {e}")
                logger.exception("Full traceback for loading error:")

    if not docs:
        logger.warning(f"No documents found in '{path}'.")
        return []

    logger.info(f"Loaded {len(docs)} documents.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunked_docs = text_splitter.split_documents(docs)
    logger.info(f"Split documents into {len(chunked_docs)} chunks.")

    return chunked_docs


from backend.weaviate_client import get_weaviate_client


def connect_to_weaviate():
    """Deprecated: use backend.weaviate_client.get_weaviate_client instead."""
    # Maintain backward compatibility for any external scripts
    return get_weaviate_client()


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
    # usedforsecurity=False is not available in all python versions, nosec is safer
    content_hash = hashlib.md5(doc.page_content.encode("utf-8")).hexdigest()  # nosec B324
    source_file = os.path.basename(doc.metadata.get("source", "unknown"))
    return hashlib.md5(f"{source_file}:{content_hash}".encode("utf-8")).hexdigest()  # nosec B324


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


def optimize_embedding_model(embedding_model: SentenceTransformer) -> SentenceTransformer:
    """Compile the embedding model with torch.compile if not already compiled.

    Adds a private marker attribute on the compiled instance to avoid duplicate work/logs.
    """
    if bool(getattr(embedding_model, "_is_torch_compiled", False)):
        return embedding_model

    try:
        logger.info("torch.compile: optimizing embedding model – this may take a minute on first run…")
        compiled_model = torch.compile(embedding_model, backend="inductor", mode="max-autotune")
        # Mark the compiled instance so future calls are a no-op.
        try:
            setattr(compiled_model, "_is_torch_compiled", True)  # type: ignore[attr-defined]
        except (AttributeError, TypeError) as attr_err:
            logger.debug("Could not set _is_torch_compiled flag on compiled model: %s", attr_err)
        logger.info("torch.compile optimization completed.")
        return cast(SentenceTransformer, compiled_model)
    except Exception as e:
        logger.warning(f"Could not apply torch.compile: {e}")
        return embedding_model


def ingest(
    directory: str,
    collection_name: str,
    weaviate_client: weaviate.WeaviateClient,
    embedding_model: SentenceTransformer,
):
    """Main ingestion pipeline."""
    start_time = time.time()

    # Apply torch.compile optimization to the embedding model (idempotent)
    embedding_model = optimize_embedding_model(embedding_model)

    chunked_docs = load_and_split_documents(directory)
    if not chunked_docs:
        return

    create_collection_if_not_exists(weaviate_client, collection_name)
    process_and_upload_chunks(weaviate_client, chunked_docs, embedding_model, collection_name)

    elapsed = time.time() - start_time
    logger.info("── Summary ─────────────────────────────")
    logger.info(f"✓ {len(chunked_docs)} chunks processed and ingested.")
    logger.info(f"Elapsed: {elapsed:.1f} s")


# --- CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents (.pdf, .md) into Weaviate.")
    parser.add_argument("--data-dir", default="../data", help="Directory with document files.")
    args = parser.parse_args()

    # Create a single Weaviate client instance
    client = connect_to_weaviate()

    # Load the embedding model once
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL, cache_folder=HF_CACHE_DIR)

    try:
        ingest(
            directory=str(args.data_dir),
            collection_name=COLLECTION_NAME,
            weaviate_client=client,
            embedding_model=model,
        )
    finally:
        client.close()
