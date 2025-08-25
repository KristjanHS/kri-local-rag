#!/usr/bin/env python3
"""E2E test: ingestion with heavy optimizations against a real Weaviate.

Uses testcontainers to start Weaviate and runs the ingestion pipeline with
real CPU torch.compile optimizations enabled. Verifies data lands in the
shared test collection and that optimization logs are emitted.
"""

import os

import pytest

pytestmark = [pytest.mark.slow]

from backend import ingest
from backend.retriever import _get_embedding_model


def test_e2e_ingest_with_heavy_optimizations_into_real_weaviate(caplog, weaviate_client, clean_test_collection):
    """Verify ingestion works against production Weaviate with torch.compile."""
    import logging

    caplog.set_level(logging.INFO, logger="backend.ingest")

    collection_name = "TestCollection"

    data_dir = os.path.join("test_data")
    embedding_model = _get_embedding_model()
    ingest.ingest(
        directory=data_dir,
        collection_name=collection_name,
        weaviate_client=weaviate_client,
        embedding_model=embedding_model,
    )

    collection = weaviate_client.collections.get(collection_name)
    count = collection.aggregate.over_all(total_count=True)
    assert count.total_count is not None and count.total_count >= 2

    msgs = [rec.getMessage() for rec in caplog.records if rec.name == "backend.ingest"]
    assert any("torch.compile optimization completed" in m for m in msgs)
