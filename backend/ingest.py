#!/usr/bin/env python3
from __future__ import annotations

"""Document Ingestion Script

This script loads documents with lightweight, permissively-licensed parsers
(pypdf for PDFs, stdlib for text) and a manual pipeline for vectorization and
storage to offer detailed control.

Usage:
    python backend/ingest.py --data-dir ./data

Key Features:
-   **Multi-Format Support**: Ingests PDF (pypdf) and Markdown (stdlib) files.
-   **Manual Control**: Provides explicit control over sentence transformation and Weaviate upsert logic.
-   **Idempotent**: Re-running the script updates existing documents without creating duplicates.
-   **CPU Optimized**: Leverages a CPU-optimized sentence-transformer model.
"""

import argparse
import hashlib
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Protocol, TypeVar, cast, runtime_checkable

import torch
import weaviate
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# Avoid importing sentence-transformers at module import time to keep imports light
# and prevent optional vision dependencies from being pulled in during unit tests.


# A minimal protocol to support our embedding calls and enable test doubles.
# Match SentenceTransformer.encode first parameter shape for compatibility.
@runtime_checkable
class SupportsEncode(Protocol):
    def encode(self, text: str, /, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        ...


# SentenceTransformer is now loaded via backend.models for consistency
from backend.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    WEAVIATE_BATCH_SIZE,
    WEAVIATE_CONCURRENT_REQUESTS,
    get_logger,
)
from backend.vector_utils import to_float_list

# --- Logging Setup ---
logger = get_logger(__name__)


def _is_valid_pdf(path: str) -> bool:
    """Defense-in-depth: confirm a .pdf file actually starts with the PDF magic bytes."""
    try:
        with open(path, "rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError:
        return False


def _load_pdf(path: str) -> List[Document]:
    """Load a PDF into one Document per page using pypdf (pure-Python, BSD-licensed)."""
    reader = PdfReader(path)
    return [
        Document(page_content=page.extract_text() or "", metadata={"source": path, "page": i})
        for i, page in enumerate(reader.pages)
    ]


def _load_text(path: str) -> List[Document]:
    """Load a UTF-8 text/markdown file into a single Document via the stdlib."""
    return [Document(page_content=Path(path).read_text(encoding="utf-8"), metadata={"source": path})]


def load_and_split_documents(path: str) -> List[Document]:
    """Load documents from a directory or a single file, then split into chunks."""
    # Fast path: if the path does not exist, skip gracefully
    if not os.path.exists(path):
        logger.warning(f"Path not found: '{path}'. Skipping ingestion.")
        return []

    # 1) Single file path support
    docs: List[Document] = []
    file_count = 0
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf" and not _is_valid_pdf(path):
            logger.warning(f"Skipping '{path}': not a valid PDF (bad magic bytes).")
            return []
        if ext in (".pdf", ".md"):
            # Same error isolation as the directory walk: a corrupt PDF or
            # non-UTF-8 file logs and yields nothing rather than aborting.
            try:
                docs.extend(_load_pdf(path) if ext == ".pdf" else _load_text(path))
                file_count = 1
            except Exception as e:
                logger.error(f"Error loading '{path}': {e}")
                logger.exception("Full traceback for loading error:")
                return []
        else:
            logger.warning(f"Unsupported file extension '{ext}' for path '{path}'.")
            return []
    else:
        # 2) Directory path with glob patterns. Per-file try/except so one bad
        #    file logs and is skipped rather than aborting the whole batch.
        import glob

        loader_configs = {
            "**/*.pdf": _load_pdf,
            "**/*.md": _load_text,
        }
        for glob_pattern, loader_fn in loader_configs.items():
            for file_path in glob.glob(os.path.join(path, glob_pattern), recursive=True):
                try:
                    if file_path.lower().endswith(".pdf") and not _is_valid_pdf(file_path):
                        logger.warning(f"Skipping '{file_path}': not a valid PDF (bad magic bytes).")
                        continue
                    docs.extend(loader_fn(file_path))
                    file_count += 1
                except Exception as e:
                    logger.error(f"Error loading '{file_path}' with pattern '{glob_pattern}': {e}")
                    logger.exception("Full traceback for loading error:")

    # Drop pages with no extractable text (e.g. image-only/scanned PDF pages):
    # empty content would yield colliding deterministic UUIDs and junk vectors.
    docs = [d for d in docs if d.page_content.strip()]

    if not docs:
        logger.warning(f"No documents found in '{path}'.")
        return []

    logger.info(f"Loaded {len(docs)} pages from {file_count} files.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunked_docs = text_splitter.split_documents(docs)
    logger.info(f"Split documents into {len(chunked_docs)} chunks.")

    return chunked_docs


from backend.weaviate_client import ensure_collection, get_weaviate_client, reset_collection


def connect_to_weaviate() -> weaviate.WeaviateClient:
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
    # Combine the source file basename with a SHA-256 of the content
    # and derive a stable RFC 4122 UUIDv5 from that name.
    content_hash = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()
    # Avoid direct attribute access that Pyright may mark as Unknown
    meta_for_uuid: dict[str, Any] = getattr(doc, "metadata", {})
    source: str = "unknown" if (source_val := meta_for_uuid.get("source")) is None else str(source_val)
    source_file = os.path.basename(source)
    name = f"{source_file}:{content_hash}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def process_and_upload_chunks(
    client: weaviate.WeaviateClient,
    docs: List[Document],
    model: SupportsEncode,
    collection_name: str,
) -> None:
    """Process each document chunk and upload it to Weaviate."""
    # Access collection (standard accessor for our tests/mocks)
    collection = client.collections.get(collection_name)
    total_chunks = len(docs)
    logger.info(f"Encoding and uploading {total_chunks} chunks… This can take a while on first run.")
    start_ts = time.time()
    last_log_ts = start_ts

    with collection.batch.fixed_size(
        batch_size=WEAVIATE_BATCH_SIZE,
        concurrent_requests=WEAVIATE_CONCURRENT_REQUESTS,
    ) as batch:
        for idx, doc in enumerate(docs, start=1):
            # Avoid direct attribute access that Pyright may mark as Unknown
            meta: dict[str, Any] = cast(dict[str, Any], getattr(doc, "metadata", {}))
            uuid = deterministic_uuid(doc)
            vector_tensor = model.encode(doc.page_content)
            # Normalize to a plain Python list of floats for the Weaviate client
            vector: List[float] = to_float_list(vector_tensor)

            src: Optional[str] = cast(Optional[str], meta.get("source", None))
            src_safe: str = src or "unknown"
            # Normalize extension to match CLI filter examples (e.g., "pdf", "md")
            ext = os.path.splitext(src_safe)[1].lstrip(".").lower()
            properties: dict[str, str] = {
                "content": doc.page_content,
                "source_file": os.path.basename(src_safe),
                "source": ext,
                # Derive created_at from source file if it exists; fall back to now.
                "created_at": _safe_created_at(src),
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

    logger.info(f"Batch ingestion complete: {total_chunks} chunks processed.")


TModel = TypeVar("TModel", bound=SupportsEncode)


def optimize_embedding_model(embedding_model: TModel) -> TModel:
    """Compile the embedding model with torch.compile if not already compiled.

    Adds a private marker attribute on the compiled instance to avoid duplicate work/logs.
    """
    if bool(getattr(embedding_model, "_is_torch_compiled", False)):
        return embedding_model

    try:
        logger.info("torch.compile: optimizing embedding model – this may take a minute on first run…")
        torch_compile = getattr(torch, "compile")
        compiled_model = cast(
            TModel,
            torch_compile(embedding_model, backend="inductor", mode="max-autotune"),
        )
        # Mark the compiled instance so future calls are a no-op.
        try:
            setattr(compiled_model, "_is_torch_compiled", True)  # type: ignore[attr-defined]
        except (AttributeError, TypeError) as attr_err:
            logger.debug("Could not set _is_torch_compiled flag on compiled model: %s", attr_err)
        logger.info("torch.compile optimization completed.")
        return compiled_model
    except Exception as e:
        logger.warning(f"Could not apply torch.compile: {e}")
        return embedding_model


def ingest(
    directory: str,
    collection_name: str,
    weaviate_client: weaviate.WeaviateClient,
    embedding_model: SupportsEncode,
    *,
    reset: bool = False,
):
    """Main ingestion pipeline."""
    start_time = time.time()

    # Apply torch.compile optimization to the embedding model (idempotent)
    embedding_model = optimize_embedding_model(embedding_model)

    chunked_docs = load_and_split_documents(directory)
    if not chunked_docs:
        return

    if reset:
        reset_collection(weaviate_client, collection_name)
    else:
        ensure_collection(weaviate_client, collection_name)
    # Narrow to the minimal protocol needed for ingestion; the concrete
    # SentenceTransformer provides a compatible .encode at runtime.
    process_and_upload_chunks(weaviate_client, chunked_docs, embedding_model, collection_name)

    elapsed = time.time() - start_time
    logger.info("── Summary ─────────────────────────────")
    logger.info(f"✓ {len(chunked_docs)} chunks processed and ingested.")
    logger.info(f"Elapsed: {elapsed:.1f} s")


# --- CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents (.pdf, .md) into Weaviate.")
    parser.add_argument("--data-dir", default="../data", help="Directory with document files.")
    parser.add_argument(
        "--reset-collection",
        action="store_true",
        default=False,
        help="Delete and recreate the collection before ingesting (default: false).",
    )
    args = parser.parse_args()

    # Create a single Weaviate client instance
    client = connect_to_weaviate()

    # Load the embedding model once
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    from backend.models import load_embedder

    model = load_embedder()

    try:
        ingest(
            directory=str(args.data_dir),
            collection_name=COLLECTION_NAME,
            weaviate_client=client,
            embedding_model=model,
            reset=bool(args.reset_collection),
        )
    finally:
        client.close()
