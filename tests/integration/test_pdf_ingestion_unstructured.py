from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from backend.ingest import load_and_split_documents


def test_pdf_ingestion_falls_back_to_unstructured(tmp_path, monkeypatch):
    """Ensure PDF ingestion works when PyMuPDF is unavailable and Unstructured is used."""
    source_pdf = Path("example_data/test.pdf")
    target_pdf = tmp_path / source_pdf.name
    shutil.copyfile(source_pdf, target_pdf)

    # Force load_and_split_documents to fall back to UnstructuredPDFLoader
    import langchain_community.document_loaders as loaders

    module_lookup = getattr(loaders, "_module_lookup", None)
    if not isinstance(module_lookup, dict):
        pytest.skip("langchain_community.document_loaders does not expose the expected module lookup map")

    if "PyMuPDFLoader" not in module_lookup:
        pytest.skip("PyMuPDFLoader not registered; fallback already active")

    patched_lookup = dict(module_lookup)
    patched_lookup.pop("PyMuPDFLoader", None)
    monkeypatch.setattr(loaders, "_module_lookup", patched_lookup)

    docs = load_and_split_documents(str(tmp_path))

    assert docs, "Expected chunks from UnstructuredPDFLoader fallback"
    # Spot-check that the PDF content made it through the loader
    assert any("Rhyme Scheme" in chunk.page_content for chunk in docs)
