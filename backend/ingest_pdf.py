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
from weaviate.util import generate_uuid5
from weaviate.exceptions import UnexpectedStatusCodeError

from config import COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP

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


splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

# ---------- helpers ----------------------------------------------------------------


def extract_text(path: str) -> str:
    if partition_pdf is None:
        raise ImportError("Install 'unstructured[pdf]' to enable PDF parsing.")

    try:
        els = partition_pdf(filename=path)
        return "\n".join([e.text for e in els if getattr(e, "text", None)])
    except Exception as err:
        print(f"[Error] Failed to parse {os.path.basename(path)} with unstructured: {err}")
        return ""


def list_pdfs(directory: str) -> List[str]:
    return glob.glob(os.path.join(directory, "*.pdf"))


def connect() -> weaviate.WeaviateClient:
    # Use local connection for v4 compatibility
    return weaviate.connect_to_local()


def ensure_collection(client: weaviate.WeaviateClient):
    if not client.collections.exists(COLLECTION_NAME):
        client.collections.create(name=COLLECTION_NAME)
    return client.collections.get(COLLECTION_NAME)


# ---------- ingestion logic ---------------------------------------------------------


def process_pdf(path: str, docs, stats: dict[str, int]):
    text = extract_text(path)
    chunks = splitter.split_text(text)
    stats["chunks"] += len(chunks)
    # Use a UUID that is independent of *content* so we can detect edits.
    for i, chunk in enumerate(chunks):
        uuid = generate_uuid5(f"{os.path.basename(path)}:{i}")
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
        docs = ensure_collection(client)
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
    parser = argparse.ArgumentParser(description="Ingest PDFs into Weaviate and print statistics.")
    parser.add_argument("--data-dir", default="../data", help="Directory with PDF files.")
    args = parser.parse_args()

    ingest(args.data_dir)
