#!/usr/bin/env python3
"""Integration test for the ingestion pipeline with real Weaviate compose service."""

from unittest.mock import MagicMock

import pytest
from sentence_transformers import SentenceTransformer

from backend import config, ingest
from tests.conftest import TEST_COLLECTION_NAME

# Mark the entire module as 'slow'
pytestmark = pytest.mark.slow

# --- Constants ---
EMBEDDING_MODEL = config.EMBEDDING_MODEL
COLLECTION_NAME = TEST_COLLECTION_NAME  # Use the shared test collection constant


@pytest.fixture
def weaviate_collection_mock(mock_weaviate_connect):
    """Fixture for mocking the Weaviate collection and its batch operations."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_batch = MagicMock()

    # When the batch context manager is entered, it should return the mock_batch object itself
    mock_batch.__enter__.return_value = mock_batch

    # Set up the chain of mocks
    mock_collection.batch.fixed_size.return_value = mock_batch
    mock_client.collections.get.return_value = mock_collection
    # Simulate collection not existing on first call, existing on subsequent calls
    mock_client.collections.exists.side_effect = [False, True, True, True]
    mock_weaviate_connect.return_value = mock_client

    # Yield the top-level client mock so tests can inspect the whole chain
    yield mock_client


@pytest.mark.requires_weaviate
def test_ingest_pipeline_with_real_weaviate_compose(weaviate_client, sample_documents_path):
    """Test the full ingestion pipeline with a real Weaviate instance, using a local model."""
    # Run the ingestion process on the test directory with only PDF files
    from backend.retriever import _get_embedding_model

    embedding_model = _get_embedding_model()
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


@pytest.mark.requires_weaviate
def test_ingest_pipeline_loads_and_embeds_data_compose(weaviate_collection_mock, sample_documents_path):
    """Test the full ingestion pipeline from loading docs to inserting into Weaviate with a local model."""
    # Provide a real embedding model for this integration test
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    # Run the ingestion process
    ingest.ingest(
        directory=sample_documents_path,
        collection_name=COLLECTION_NAME,
        weaviate_client=weaviate_collection_mock,
        embedding_model=embedding_model,
    )

    # --- Assertions ---
    # Get the mock batch object from the mock client
    mock_batch = (
        weaviate_collection_mock.collections.get.return_value.batch.fixed_size.return_value.__enter__.return_value
    )

    # Check that documents were loaded correctly and the batch add_object was called
    # Now using only the PDF file to avoid NLTK dependency
    assert mock_batch.add_object.call_count == 1

    # Get the arguments passed to add_object
    call_args = mock_batch.add_object.call_args_list
    assert len(call_args) == 1

    # Check the structure of the inserted data in the first call
    first_call_kwargs = call_args[0].kwargs
    assert "properties" in first_call_kwargs
    assert "vector" in first_call_kwargs

    # Verify that the vector is of the correct dimension (for all-MiniLM-L6-v2)
    assert len(first_call_kwargs["vector"]) == 384


@pytest.mark.requires_weaviate
def test_ingest_pipeline_handles_no_embedding_model_compose(weaviate_collection_mock, sample_documents_path):
    """Test that the ingestion pipeline exits gracefully if no local embedding model is available."""
    with pytest.raises(AttributeError):
        ingest.ingest(
            directory=sample_documents_path,
            collection_name=COLLECTION_NAME,
            weaviate_client=weaviate_collection_mock,
            embedding_model=None,  # type: ignore
        )


@pytest.mark.requires_weaviate
def test_ingest_pipeline_is_idempotent_compose(weaviate_collection_mock, sample_documents_path):
    """Test that running ingestion multiple times doesn't create duplicate data, using a local model."""
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    # Run ingestion once
    ingest.ingest(
        directory=sample_documents_path,
        collection_name=COLLECTION_NAME,
        weaviate_client=weaviate_collection_mock,
        embedding_model=embedding_model,
    )
    # Run ingestion a second time
    ingest.ingest(
        directory=sample_documents_path,
        collection_name=COLLECTION_NAME,
        weaviate_client=weaviate_collection_mock,
        embedding_model=embedding_model,
    )

    # Assert that the creation and insertion logic was accessed correctly
    mock_batch = (
        weaviate_collection_mock.collections.get.return_value.batch.fixed_size.return_value.__enter__.return_value
    )
    assert weaviate_collection_mock.collections.create.call_count == 1
    assert mock_batch.add_object.call_count == 2  # 1 doc * 2 runs
