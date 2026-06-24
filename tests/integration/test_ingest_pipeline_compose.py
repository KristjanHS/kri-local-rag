#!/usr/bin/env python3
"""Integration test for the ingestion pipeline with real Weaviate compose service."""

import pytest

from backend import ingest
from tests.conftest import TEST_COLLECTION_NAME

# Integration test for the ingestion pipeline with real Weaviate compose service

# --- Constants ---
COLLECTION_NAME = TEST_COLLECTION_NAME  # Use the shared test collection constant


@pytest.mark.requires_weaviate
def test_ingest_pipeline_with_real_weaviate_compose(weaviate_client, sample_documents_path):
    """Test the full ingestion pipeline with a real Weaviate instance, using a local model."""
    # Run the ingestion process on the test directory with only PDF files
    from backend.models import load_embedder

    embedding_model = load_embedder()
    ingest.ingest(
        directory=sample_documents_path,
        collection_name=COLLECTION_NAME,
        weaviate_client=weaviate_client,
        embedding_model=embedding_model,
    )

    # --- Assertions ---
    # Check that the collection was created and contains the correct number of documents
    collection = weaviate_client.collections.get(COLLECTION_NAME)
    count = collection.aggregate.over_all(total_count=True)
    assert count.total_count == 1  # Only test.pdf (no markdown files to avoid NLTK dependency)
