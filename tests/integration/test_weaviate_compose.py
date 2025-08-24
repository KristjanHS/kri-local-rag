#!/usr/bin/env python3
"""Integration tests for Weaviate using Docker Compose - runs inside container."""

import logging
import time

import weaviate
from weaviate.classes.config import DataType, Property

from tests.integration.conftest import get_weaviate_hostname

logger = logging.getLogger(__name__)


def test_weaviate_service_is_ready():
    """Verify that the Weaviate service is ready to accept connections."""
    # Use dynamic hostname detection to work in both Docker and local environments
    weaviate_host = get_weaviate_hostname()
    logger.info(f"Connecting to Weaviate at {weaviate_host}:8080")
    client = weaviate.connect_to_local(
        host=weaviate_host,
        port=8080,
        grpc_port=50051,
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
        logger.info("✓ Weaviate service is ready and accepting connections")
    finally:
        client.close()


def test_weaviate_basic_operations():
    """Test basic Weaviate operations to ensure the service is fully functional."""
    # Use dynamic hostname detection to work in both Docker and local environments
    weaviate_host = get_weaviate_hostname()
    logger.info(f"Connecting to Weaviate at {weaviate_host}:8080 for basic operations test")
    client = weaviate.connect_to_local(
        host=weaviate_host,
        port=8080,
        grpc_port=50051,
    )

    try:
        # Test basic connectivity
        assert client.is_ready()

        # Test schema operations using the correct API
        schema = client.collections.list_all()
        assert schema is not None

        # Test that we can create a simple collection
        collection_name = "test_collection"

        # Clean up any existing test collection
        try:
            client.collections.delete(collection_name)
        except Exception:
            pass  # Collection doesn't exist

        # Create a simple test collection
        client.collections.create(
            name=collection_name,
            properties=[
                Property(name="content", data_type=DataType.TEXT),
            ],
        )

        # Verify the collection was created
        collections = client.collections.list_all()
        collection_names = [c for c in collections]
        # Weaviate may return the collection name with different casing
        assert collection_name.lower() in [c.lower() for c in collection_names]

        # Clean up
        client.collections.delete(collection_name)

        logger.info("✓ Weaviate basic operations test passed")

    finally:
        client.close()
