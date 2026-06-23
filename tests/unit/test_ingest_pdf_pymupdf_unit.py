#!/usr/bin/env python3
"""Functional test: ingest's PDF path loads real PDFs via the pymupdf backend.

pymupdf is a transitive PDF backend that no app code imports directly, so a
broken/missing wheel stays invisible to the rest of the suite — it only
surfaces when the Docker build source-compiles it and dies. (1.24.x ships no
cp313 wheel; see the ``pymupdf>=1.25.0`` pin in pyproject.toml.) This test
drives ``backend.ingest.load_and_split_documents`` through its ``PyMuPDFLoader``
branch on a committed PDF fixture so a broken pymupdf fails fast and locally.
"""

from __future__ import annotations

from pathlib import Path

from backend import ingest as ing

# Marker text embedded in tests/test_data/test.pdf (regenerate the fixture if changed).
MARKER = "Kri local RAG pymupdf backend smoke marker"
FIXTURE = Path(__file__).resolve().parents[1] / "test_data" / "test.pdf"


def test_load_and_split_pdf_via_pymupdf():
    assert FIXTURE.is_file(), f"missing PDF fixture: {FIXTURE}"

    chunks = ing.load_and_split_documents(str(FIXTURE))

    assert chunks, "expected at least one chunk from the PDF"

    combined = " ".join(c.page_content for c in chunks)
    assert MARKER in combined, f"extracted text missing marker; got {combined!r}"

    meta = chunks[0].metadata
    # `format` (e.g. "PDF 1.7") is emitted by PyMuPDFLoader, not the PyPDFLoader
    # fallback — asserting it confirms the pymupdf backend was actually exercised.
    assert meta.get("format", "").startswith("PDF"), f"expected PyMuPDFLoader metadata; got keys {sorted(meta)}"
    assert meta.get("source", "").endswith("test.pdf")
