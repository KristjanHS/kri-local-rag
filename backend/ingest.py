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
from typing import List

import torch
import weaviate
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
)
from sentence_transformers import SentenceTransformer

from backend.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    WEAVIATE_URL,
    get_logger,
)

# --- Logging Setup ---
logger = get_logger(__name__)


def load_and_split_documents(directory: str) -> List[Document]:
    """Load documents using LangChain and split them into chunks."""
    loader_configs = {
        "**/*.pdf": PyPDFLoader,
        "**/*.md": UnstructuredMarkdownLoader,
    }
    docs = []
    for glob_pattern, loader_cls in loader_configs.items():
        loader = DirectoryLoader(
            directory,
            glob=glob_pattern,
            loader_cls=loader_cls,
            show_progress=True,
            use_multithreading=True,
        )
        docs.extend(loader.load())

    if not docs:
        logger.warning(f"No documents found in '{directory}'.")
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
        http_host=parsed_url.hostname,
        http_port=parsed_url.port or 80,
        grpc_host=parsed_url.hostname,
        grpc_port=50051,
        http_secure=parsed_url.scheme == "https",
        grpc_secure=parsed_url.scheme == "https",
    )
    logger.info("Connection successful.")
    return client


def _safe_created_at(source_path: str | None) -> str:
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
    """Create the collection in Weaviate if it doesn't exist."""
    if not client.collections.exists(collection_name):
        client.collections.create(
            name=collection_name,
            # The vectorizer is set to "none" because we are providing our own vectors.
            # Weaviate will not generate vectors for us.
            vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
            # The generative module is set to "none" as we are using a separate LLM.
            # generative_config=weaviate.classes.config.Configure.Generative.none(),
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
    collection = client.collections.get(collection_name)
    stats = {"inserts": 0, "updates": 0, "skipped": 0}

    with collection.batch.dynamic() as batch:
        for doc in docs:
            uuid = deterministic_uuid(doc)
            vector = model.encode(doc.page_content)

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

    logger.info(f"Batch ingestion complete: {stats}")
    return stats


def ingest(directory: str, collection_name: str = COLLECTION_NAME):
    """Main ingestion pipeline."""
    start_time = time.time()

    chunked_docs = load_and_split_documents(directory)
    if not chunked_docs:
        return

    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    try:
        logger.info("torch.compile: optimizing embedding model – this may take a minute on first run…")
        model = torch.compile(model, backend="inductor", mode="max-autotune")
        logger.info("torch.compile optimization completed.")
    except Exception as e:
        logger.warning(f"Could not apply torch.compile: {e}")

    client = connect_to_weaviate()
    try:
        create_collection_if_not_exists(client, collection_name)
        process_and_upload_chunks(client, chunked_docs, model, collection_name)
    finally:
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
    ingest(args.data_dir)
