#!/usr/bin/env python3
"""PDF → Weaviate ingestion with run statistics.

Usage
-----
$ python ingest_pdf.py --data-dir ./data

The script will:
1. Connect to a **local** Weaviate instance.
2. Ensure the collection defined in config.COLLECTION_NAME exists.
3. Walk through all *.pdf files in --data-dir.
4. Split each PDF into chunks and *upsert* them with deterministic UUIDs so re-runs never create duplicates.

After processing it prints e.g.
✓ 3 PDFs processed
✓ 142 chunks (90 inserts, 52 updates)
Elapsed: 4.3 s
"""

from __future__ import annotations

import argparse
import glob
import os
import time
from datetime import datetime, timezone
from typing import List

import weaviate
import torch
from langchain.text_splitter import RecursiveCharacterTextSplitter
from weaviate.exceptions import UnexpectedStatusCodeError
from weaviate.classes.config import Property, DataType

from config import COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP, WEAVIATE_URL, get_logger
from urllib.parse import urlparse

# Set up logging for this module
logger = get_logger(__name__)

# Debug helpers
import hashlib
import traceback

# Lightweight language detection
try:
    from langdetect import detect
except ImportError:
    detect = None  # type: ignore

# For manual vectorization
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:
    SentenceTransformer = None  # type: ignore

# ---------- optional PDF back-ends --------------------------------------------------
try:
    from unstructured.partition.pdf import partition_pdf  # type: ignore
except ImportError:
    # Provide detailed diagnostics so we know *why* the import failed.
    logger.debug("Failed to import 'unstructured.partition.pdf'. Full traceback follows:")
    traceback.print_exc()

    # Check if the base package is present at all and print its version.
    try:
        import importlib.metadata as _metadata

        logger.debug("Detected unstructured version: %s", _metadata.version("unstructured"))
    except Exception:
        logger.warning("Package 'unstructured' is not installed in this environment.")

    # Fallback: disable PDF parsing so the rest of the script can continue.
    partition_pdf = None

# Remove PyPDF fallback – rely solely on `unstructured`.
PdfReader = None


splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

# ---------- helpers ----------------------------------------------------------------


def extract_text(path: str) -> str:
    if partition_pdf is None:
        raise ImportError("Install 'unstructured[pdf]' to enable PDF parsing.")

    try:
        els = partition_pdf(filename=path, languages=["eng"])
        return "\n".join([e.text for e in els if getattr(e, "text", None)])
    except Exception as err:
        logger.error("Failed to parse %s with unstructured: %s", os.path.basename(path), err)
        return ""


def list_pdfs(directory: str) -> List[str]:
    return glob.glob(os.path.join(directory, "*.pdf"))


def connect() -> weaviate.WeaviateClient:
    parsed_url = urlparse(WEAVIATE_URL)
    return weaviate.connect_to_custom(
        http_host=parsed_url.hostname,
        http_port=parsed_url.port or 80,
        grpc_host=parsed_url.hostname,
        grpc_port=50051,
        http_secure=parsed_url.scheme == "https",
        grpc_secure=parsed_url.scheme == "https",
    )


def create_collection_if_not_exists(client: weaviate.WeaviateClient):
    """Create the collection with a predefined schema if it doesn't exist."""
    if not client.collections.exists(COLLECTION_NAME):
        client.collections.create(
            name=COLLECTION_NAME,
            properties=[
                Property(name="content", data_type=DataType.TEXT),
                Property(name="source_file", data_type=DataType.TEXT),
                Property(name="page", data_type=DataType.INT),
                Property(name="source", data_type=DataType.TEXT),
                Property(name="section", data_type=DataType.TEXT),
                Property(name="created_at", data_type=DataType.DATE),
                Property(name="language", data_type=DataType.TEXT),
            ],
            # No vectorizer_config means we provide vectors manually
        )
        logger.info("→ Collection '%s' created for manual vectorization.", COLLECTION_NAME)


def get_collection(client: weaviate.WeaviateClient):
    return client.collections.get(COLLECTION_NAME)


def deterministic_uuid(source_file, chunk_index, chunk_content):
    base = f"{source_file}:{chunk_index}:{chunk_content}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


# ---------- ingestion logic ---------------------------------------------------------


def process_pdf(path: str, docs, stats: dict[str, int], model: "SentenceTransformer"):
    text = extract_text(path)
    chunks = splitter.split_text(text)
    stats["chunks"] += len(chunks)
    # Use a UUID that is independent of *content* so we can detect edits.
    for i, chunk in enumerate(chunks):
        uuid = deterministic_uuid(os.path.basename(path), i, chunk)
        # Basic metadata enrichment
        created_ts = os.path.getmtime(path)
        # RFC3339 requires explicit timezone. Use UTC (Z) to satisfy Weaviate.
        created_iso = datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat()

        if detect is not None:
            try:
                language = detect(chunk[:400])  # use first few hundred chars for speed
            except Exception:
                language = "unknown"
        else:
            language = "unknown"

        props = {
            "content": chunk,
            "page": i,
            "source_file": os.path.basename(path),
            "source": "pdf",
            "section": "body",
            "created_at": created_iso,
            "language": language,
        }

        vector = model.encode(chunk)

        try:
            # First try to insert – fast path for new chunks
            docs.data.insert(uuid=uuid, properties=props, vector=vector)
            stats["inserts"] += 1
        except UnexpectedStatusCodeError as e:
            # 422 "id already exists" → object present; decide if update needed
            if "already exists" not in str(e):  # different error, re-raise
                raise

            try:
                existing = docs.data.get(uuid=uuid)
            except Exception:
                existing = None

            if existing and existing.properties.get("content", "") != chunk:
                docs.data.replace(uuid=uuid, properties=props, vector=vector)
                stats["updates"] += 1
            else:
                stats["skipped"] += 1


def ingest(directory: str):
    if SentenceTransformer is None:
        raise ImportError("Install 'sentence-transformers' to enable vectorization.")

    # Suppress FutureWarning from PyTorch about deprecated encoder_attention_mask
    # Can be disabled by setting SUPPRESS_TORCH_WARNINGS=false
    if os.getenv("SUPPRESS_TORCH_WARNINGS", "true").lower() != "false":
        import warnings

        warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.modules.module")

    # Alternative models that may have fewer warnings:
    # - "sentence-transformers/all-mpnet-base-v2" (768d, better quality)
    # - "sentence-transformers/multi-qa-MiniLM-L6-cos-v1" (384d, similar to current)
    # - "sentence-transformers/paraphrase-MiniLM-L6-v2" (384d, alternative)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # Apply PyTorch CPU optimizations
    # Set optimal threading for current environment
    torch.set_num_threads(12)  # Oversubscribe lightly to hide I/O stalls

    # Apply torch.compile with max-autotune for 5-25% speed-ups on CPU GEMM-heavy models
    try:
        model = torch.compile(model, backend="inductor", mode="max-autotune")
        logger.info("Applied torch.compile optimization to embedding model for ingestion")
    except Exception as compile_e:
        logger.warning("Failed to apply torch.compile optimization: %s", compile_e)

    pdfs = list_pdfs(directory)
    if not pdfs:
        logger.warning("No PDF files in '%s'.", directory)
        return

    stats = {"pdfs": len(pdfs), "chunks": 0, "inserts": 0, "updates": 0, "skipped": 0}
    start = time.time()

    client = connect()
    try:
        create_collection_if_not_exists(client)
        docs = get_collection(client)
        for p in pdfs:
            logger.info("→ %s", os.path.basename(p))
            process_pdf(p, docs, stats, model)
    finally:
        client.close()

    elapsed = time.time() - start
    # ---------- summary ---------------------------------------------------------
    logger.info("── Summary ─────────────────────────────")
    logger.info("✓ %d PDF(s) processed", stats["pdfs"])
    logger.info(
        "✓ %d chunks  (%d inserts, %d updates, %d skipped)",
        stats["chunks"],
        stats["inserts"],
        stats["updates"],
        stats["skipped"],
    )
    logger.info("Elapsed: %.1f s", elapsed)


# ---------- CLI ---------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDFs into Weaviate and print statistics.")
    parser.add_argument("--data-dir", default="../data", help="Directory with PDF files.")
    args = parser.parse_args()

    ingest(args.data_dir)
