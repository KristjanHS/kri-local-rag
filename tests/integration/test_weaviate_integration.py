#!/usr/bin/env python3
"""Integration tests for Weaviate using testcontainers."""

import pytest
from testcontainers.weaviate import WeaviateContainer


@pytest.mark.slow
def test_weaviate_container_starts():
    """Verify that the Weaviate container starts and is accessible."""
    with WeaviateContainer() as weaviate_container:
        assert weaviate_container.get_container_host_ip() is not None
        client = weaviate_container.get_client()
        try:
            assert client.is_ready()
        finally:
            client.close()
