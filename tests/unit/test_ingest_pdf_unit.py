#!/usr/bin/env python3
"""Functional test: ingest's PDF path loads real PDFs via pypdf.

No app code imports the PDF backend directly, so the PDF ingestion path had no
functional coverage before this test. It drives
``backend.ingest.load_and_split_documents`` over a committed PDF fixture,
asserting the marker text is extracted and our per-page metadata is set. (pypdf
is pure-Python, so the older "catch a missing cp313 wheel" rationale no longer
applies — the retained value is exercising the real PDF path end to end.)
"""

from __future__ import annotations

from pathlib import Path

from backend import ingest as ing

# Marker text embedded in tests/test_data/test.pdf (regenerate the fixture if changed).
MARKER = "Kri local RAG pymupdf backend smoke marker"
FIXTURE = Path(__file__).resolve().parents[1] / "test_data" / "test.pdf"


def test_load_and_split_pdf_via_pypdf():
    assert FIXTURE.is_file(), f"missing PDF fixture: {FIXTURE}"

    chunks = ing.load_and_split_documents(str(FIXTURE))

    assert chunks, "expected at least one chunk from the PDF"

    combined = " ".join(c.page_content for c in chunks)
    assert MARKER in combined, f"extracted text missing marker; got {combined!r}"

    meta = chunks[0].metadata
    # Our _load_pdf sets these two keys per page; downstream ingestion consumes
    # only page_content + metadata["source"].
    assert meta.get("source", "").endswith("test.pdf")
    assert meta.get("page") == 0
