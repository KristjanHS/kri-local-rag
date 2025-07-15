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
from datetime import datetime
from typing import List

import weaviate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from weaviate.exceptions import UnexpectedStatusCodeError
from weaviate.classes.config import Configure, Property, DataType

from config import COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP, WEAVIATE_URL
from urllib.parse import urlparse

import hashlib

# Lightweight language detection
try:
    from langdetect import detect
except ImportError:
    detect = None  # type: ignore

# ---------- optional PDF back-ends --------------------------------------------------
try:
    from unstructured.partition.pdf import partition_pdf  # type: ignore
except ImportError:
    partition_pdf = None

# Remove PyPDF fallback – rely solely on `unstructured`.
PdfReader = None


splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
)

# ---------- helpers ----------------------------------------------------------------


def extract_text(path: str) -> str:
    if partition_pdf is None:
        raise ImportError("Install 'unstructured[pdf]' to enable PDF parsing.")

    try:
        els = partition_pdf(filename=path)
        return "\n".join([e.text for e in els if getattr(e, "text", None)])
    except Exception as err:
        print(
            f"[Error] Failed to parse {os.path.basename(path)} with unstructured: {err}"
        )
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
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
        )
        print(f"→ Collection '{COLLECTION_NAME}' created with the specified schema.")


def get_collection(client: weaviate.WeaviateClient):
    return client.collections.get(COLLECTION_NAME)


def deterministic_uuid(source_file, chunk_index, chunk_content):
    base = f"{source_file}:{chunk_index}:{chunk_content}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


# ---------- ingestion logic ---------------------------------------------------------


def process_pdf(path: str, docs, stats: dict[str, int]):
    text = extract_text(path)
    chunks = splitter.split_text(text)
    stats["chunks"] += len(chunks)
    # Use a UUID that is independent of *content* so we can detect edits.
    for i, chunk in enumerate(chunks):
        uuid = deterministic_uuid(os.path.basename(path), i, chunk)
        # Basic metadata enrichment
        created_ts = os.path.getmtime(path)
        created_iso = datetime.fromtimestamp(created_ts).isoformat()

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

        try:
            # First try to insert – fast path for new chunks
            docs.data.insert(uuid=uuid, properties=props)
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
                docs.data.replace(uuid=uuid, properties=props)
                stats["updates"] += 1
            else:
                stats["skipped"] += 1


def ingest(directory: str):
    pdfs = list_pdfs(directory)
    if not pdfs:
        print(f"No PDF files in '{directory}'.")
        return

    stats = {"pdfs": len(pdfs), "chunks": 0, "inserts": 0, "updates": 0, "skipped": 0}
    start = time.time()

    client = connect()
    try:
        create_collection_if_not_exists(client)
        docs = get_collection(client)
        for p in pdfs:
            print(f"→ {os.path.basename(p)}")
            process_pdf(p, docs, stats)
    finally:
        client.close()

    elapsed = time.time() - start
    # ---------- summary ---------------------------------------------------------
    print("\n── Summary ─────────────────────────────")
    print(f"✓ {stats['pdfs']} PDF(s) processed")
    print(
        f"✓ {stats['chunks']} chunks  ("
        f"{stats['inserts']} inserts, {stats['updates']} updates, {stats['skipped']} skipped)"
    )
    print(f"Elapsed: {elapsed:.1f} s")


# ---------- CLI ---------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest PDFs into Weaviate and print statistics."
    )
    parser.add_argument(
        "--data-dir", default="../data", help="Directory with PDF files."
    )
    args = parser.parse_args()

    ingest(args.data_dir)
