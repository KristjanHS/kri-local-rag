#!/usr/bin/env python3
"""E2E test: ingestion with heavy optimizations against a real Weaviate.

Uses testcontainers to start Weaviate and runs the ingestion pipeline with
real CPU torch.compile optimizations enabled. Verifies data lands in the
shared test collection and that optimization logs are emitted.
"""

import os

import pytest
from testcontainers.weaviate import WeaviateContainer

pytestmark = [pytest.mark.slow, pytest.mark.e2e]


def test_e2e_ingest_with_heavy_optimizations_into_real_weaviate(caplog):
    # Ensure INFO logs are captured
    import logging

    caplog.set_level(logging.INFO, logger="backend.ingest")

    # Start a real Weaviate via testcontainers
    with WeaviateContainer() as weaviate_container:
        client = weaviate_container.get_client()

        # Use the same collection name as other Weaviate tests
        collection_name = "TestCollection"

        # Clean existing collection if present
        try:
            if client.collections.exists(collection_name):
                client.collections.delete(collection_name)
        except Exception:
            pass

        # Run ingestion with heavy optimizations (ingest.py already applies torch.compile)
        from backend import ingest

        # Point to the built-in test data used by other tests
        data_dir = os.path.join("test_data")

        from backend.retriever import _get_embedding_model

        embedding_model = _get_embedding_model()
        ingest.ingest(
            directory=data_dir,
            collection_name=collection_name,
            weaviate_client=client,
            embedding_model=embedding_model,
        )

    # Verify data was ingested
    collection = client.collections.get(collection_name)
    count = collection.aggregate.over_all(total_count=True)
    assert count.total_count is not None and count.total_count >= 2  # expect at least markdown and pdf entries

    # Verify optimization message appeared in logs
    msgs = [rec.getMessage() for rec in caplog.records if rec.name == "backend.ingest"]
    assert any("torch.compile optimization completed" in m for m in msgs)
