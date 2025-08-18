#!/usr/bin/env python3
"""Integration tests for Weaviate using testcontainers."""

import time

import pytest
from testcontainers.core.generic import GenericContainer


@pytest.mark.slow
def test_weaviate_container_starts():
    """Verify that the Weaviate container starts and is accessible."""
    # Use the same Weaviate image as docker-compose.yml
    weaviate_image = "cr.weaviate.io/semitechnologies/weaviate:1.32.0"
    with GenericContainer(weaviate_image) as weaviate_container:
        # Configure Weaviate container with the same settings as docker-compose.yml
        weaviate_container.with_exposed_ports(8080, 50051)
        weaviate_container.with_env("QUERY_DEFAULTS_LIMIT", "25")
        weaviate_container.with_env("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
        weaviate_container.with_env("DEFAULT_VECTORIZER_MODULE", "none")
        weaviate_container.with_env("CLUSTER_HOSTNAME", "node1")

        # Start the container
        weaviate_container.start()

        # Get the client connection details
        host = weaviate_container.get_container_host_ip()
        port = weaviate_container.get_exposed_port(8080)

        # Import weaviate client and create connection
        import weaviate

        client = weaviate.connect_to_custom(
            http_host=host,
            http_port=int(port),
            grpc_host=host,
            grpc_port=50051,
            http_secure=False,
            grpc_secure=False,
        )

        # Wait for Weaviate to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                if client.is_ready():
                    break
            except Exception:
                if i == max_retries - 1:
                    raise
                time.sleep(2)

        try:
            assert client.is_ready()
        finally:
            client.close()
