#!/usr/bin/env python3
"""Integration tests for Weaviate using simplified pytest-native patterns."""

import logging

import pytest
import weaviate
from weaviate.classes.config import DataType, Property

logger = logging.getLogger(__name__)


@pytest.mark.requires_weaviate
def test_weaviate_service_is_ready(integration):
    """Verify that the Weaviate service is ready to accept connections."""
    # Get Weaviate URL using the integration fixture
    weaviate_url = integration["get_service_url"]("weaviate")
    hostname = weaviate_url.replace("http://", "").replace(":8080", "")

    logger.info(f"Connecting to Weaviate at {hostname}:8080")
    client = weaviate.connect_to_custom(
        http_host=hostname,
        http_port=8080,
        grpc_host=hostname,
        grpc_port=50051,
        http_secure=False,
        grpc_secure=False,
    )

    try:
        assert client.is_ready()
        logger.info("✓ Weaviate service is ready and accepting connections")
    finally:
        client.close()


@pytest.mark.requires_weaviate
def test_weaviate_basic_operations(integration):
    """Test basic Weaviate operations to ensure the service is fully functional."""
    # Get Weaviate URL using the integration fixture
    weaviate_url = integration["get_service_url"]("weaviate")
    hostname = weaviate_url.replace("http://", "").replace(":8080", "")

    logger.info(f"Connecting to Weaviate at {hostname}:8080 for basic operations test")
    client = weaviate.connect_to_custom(
        http_host=hostname,
        http_port=8080,
        grpc_host=hostname,
        grpc_port=50051,
        http_secure=False,
        grpc_secure=False,
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
