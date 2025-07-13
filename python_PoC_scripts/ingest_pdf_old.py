#!/usr/bin/env python3
"""PDF → Weaviate ingestion script.

Usage
-----
$ python ingest_pdf.py --data-dir ./data

The script will:
1. Connect to a **local** Weaviate instance.
2. Ensure the collection defined in config.COLLECTION_NAME exists.
3. Walk through all *.pdf files in --data-dir.
4. Split each PDF into chunks and *upsert* them with deterministic UUIDs so re-runs never create duplicates.
"""
from __future__ import annotations

import argparse
import glob
import os
from typing import List

import weaviate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from weaviate.util import generate_uuid5

from config import COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP

# Optional PDF back-ends -------------------------------------------------------
try:
    from unstructured.partition.pdf import partition_pdf  # type: ignore
except ImportError:
    partition_pdf = None

try:
    from pypdf import PdfReader  # type: ignore
except ImportError:
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except ImportError:
        PdfReader = None


splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_text(pdf_path: str) -> str:
    """Return plain-text from a single PDF file.
    Tries *unstructured* first, then (Py)PDF if available.
    """
    if partition_pdf is not None:
        elements = partition_pdf(filename=pdf_path)
        return "\n".join([e.text for e in elements if hasattr(e, "text") and e.text])
    if PdfReader is not None:
        reader = PdfReader(pdf_path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    raise ImportError("Install either 'unstructured[pdf]' or 'pypdf' for PDF parsing.")


def list_pdf_files(directory: str) -> List[str]:
    return glob.glob(os.path.join(directory, "*.pdf"))


def connect() -> weaviate.WeaviateClient:
    return weaviate.connect_to_local()


def ensure_collection(client: weaviate.WeaviateClient):
    if not client.collections.exists(COLLECTION_NAME):
        client.collections.create(name=COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' created.")
    return client.collections.get(COLLECTION_NAME)


def upsert_pdf(pdf_path: str, docs):
    raw_text = extract_text(pdf_path)
    source_file = os.path.basename(pdf_path)
    chunks = splitter.split_text(raw_text)

    for i, chunk in enumerate(chunks):
        uuid = generate_uuid5(f"{source_file}:{i}:{chunk}")
        props = {"content": chunk, "page": i, "source_file": source_file}
        try:
            docs.data.replace(uuid=uuid, properties=props)
        except Exception:
            docs.data.insert(uuid=uuid, properties=props)


def ingest(directory: str):
    pdf_files = list_pdf_files(directory)
    if not pdf_files:
        print(f"No PDF files found in '{directory}'.")
        return

    client = connect()
    try:
        docs = ensure_collection(client)
        for path in pdf_files:
            print(f"→ Ingesting {path} …")
            upsert_pdf(path, docs)
    finally:
        client.close()
        print("✔ Done – connection closed.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ingest all PDFs in a directory into Weaviate.")
    ap.add_argument("--data-dir", default="data", help="Directory containing PDF files.")
    args = ap.parse_args()

    ingest(args.data_dir)
