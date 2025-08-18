#!/usr/bin/env python3
"""E2E test: ingestion with heavy optimizations against a real Weaviate.

Uses testcontainers to start Weaviate and runs the ingestion pipeline with
real CPU torch.compile optimizations enabled. Verifies data lands in the
shared test collection and that optimization logs are emitted.
"""

import os

import pytest
import weaviate
from testcontainers.core.container import DockerContainer

pytestmark = [pytest.mark.slow]

from testcontainers.core.waiting_utils import wait_for_logs

from backend import ingest
from backend.retriever import _get_embedding_model


def test_e2e_ingest_with_heavy_optimizations_into_real_weaviate(caplog):
    """Verify ingestion works against a real Weaviate with torch.compile."""
    import logging

    caplog.set_level(logging.INFO, logger="backend.ingest")

    weaviate_image = "cr.weaviate.io/semitechnologies/weaviate:1.32.0"
    with DockerContainer(weaviate_image) as weaviate_container:
        weaviate_container.with_exposed_ports(8080)
        weaviate_container.with_env("QUERY_DEFAULTS_LIMIT", "25")
        weaviate_container.with_env("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
        weaviate_container.with_env("DEFAULT_VECTORIZER_MODULE", "none")
        weaviate_container.with_env("CLUSTER_HOSTNAME", "node1")
        wait_for_logs(weaviate_container, "Weaviate is ready!")

        host = weaviate_container.get_container_host_ip()
        port = weaviate_container.get_exposed_port(8080)

        client = weaviate.connect_to_custom(
            http_host=host,
            http_port=int(port),
            grpc_host=host,
            grpc_port=50051,
            http_secure=False,
            grpc_secure=False,
        )
        collection_name = "TestCollection"

        if client.collections.exists(collection_name):
            client.collections.delete(collection_name)

        data_dir = os.path.join("test_data")
        embedding_model = _get_embedding_model()
        ingest.ingest(
            directory=data_dir,
            collection_name=collection_name,
            weaviate_client=client,
            embedding_model=embedding_model,
        )

        collection = client.collections.get(collection_name)
        count = collection.aggregate.over_all(total_count=True)
        assert count.total_count is not None and count.total_count >= 2

        msgs = [rec.getMessage() for rec in caplog.records if rec.name == "backend.ingest"]
        assert any("torch.compile optimization completed" in m for m in msgs)
