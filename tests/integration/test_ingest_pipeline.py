#!/usr/bin/env python3
"""Integration tests for the ingestion pipeline."""

import pytest
from langchain.docstore.document import Document
from sentence_transformers import SentenceTransformer
from testcontainers.weaviate import WeaviateContainer

from backend.config import COLLECTION_NAME, EMBEDDING_MODEL
from backend.ingest import process_and_upload_chunks


@pytest.mark.integration
def test_ingestion_pipeline():
    """Test the full ingestion pipeline with a real Weaviate instance."""
    with WeaviateContainer() as weaviate_container:
        client = weaviate_container.get_client()

        # Create the collection
        client.collections.create(COLLECTION_NAME)

        # Mock documents
        docs = [Document(page_content="This is a test document.", metadata={"source": "test.txt"})]

        # Load the model
        model = SentenceTransformer(EMBEDDING_MODEL)

        # Run the ingestion process
        process_and_upload_chunks(client, docs, model)

        # Verify the data is in Weaviate
        collection = client.collections.get(COLLECTION_NAME)
        assert len(list(collection.iterator())) == 1

        client.collections.delete(COLLECTION_NAME)
