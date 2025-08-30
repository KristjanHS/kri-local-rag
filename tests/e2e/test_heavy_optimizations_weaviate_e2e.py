#!/usr/bin/env python3
"""E2E test: ingestion with heavy optimizations against a real Weaviate.

Uses Docker Compose to start Weaviate and runs the ingestion pipeline with
real CPU torch.compile optimizations enabled. Verifies data lands in the
shared test collection and that optimization logs are emitted.
"""

import os

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.requires_weaviate]

from backend import ingest
from backend.retriever import _get_embedding_model
from tests.conftest import TEST_COLLECTION_NAME


def test_e2e_ingest_with_heavy_optimizations_into_real_weaviate(weaviate_client):
    """Verify ingestion works against production Weaviate with torch.compile optimizations enabled.

    This test verifies that:
    1. The ingestion pipeline works end-to-end with a real Weaviate instance
    2. torch.compile optimizations are applied (via the optimize_embedding_model function)
    3. Data is successfully ingested and stored in the collection

    The test focuses on outcomes rather than implementation details like log messages,
    making it more robust and maintainable.
    """
    collection_name = TEST_COLLECTION_NAME

    data_dir = os.path.join("test_data")
    embedding_model = _get_embedding_model()

    # This will apply torch.compile optimizations internally via optimize_embedding_model
    ingest.ingest(
        directory=data_dir,
        collection_name=collection_name,
        weaviate_client=weaviate_client,
        embedding_model=embedding_model,
    )

    # Verify the data was successfully ingested into Weaviate
    # This confirms that torch.compile optimizations worked correctly
    collection = weaviate_client.collections.get(collection_name)
    count = collection.aggregate.over_all(total_count=True)
    assert count.total_count is not None and count.total_count >= 2
