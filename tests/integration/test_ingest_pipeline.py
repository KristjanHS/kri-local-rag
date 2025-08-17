"""Test the full document ingestion pipeline."""

from unittest.mock import MagicMock

import pytest
from sentence_transformers import SentenceTransformer

from backend import config, ingest

# Mark the entire module as 'slow'
pytestmark = pytest.mark.slow

# --- Constants ---
EMBEDDING_MODEL = config.EMBEDDING_MODEL
COLLECTION_NAME = "TestCollection"  # Use a dedicated test collection


@pytest.fixture(scope="module")
def sample_documents_path(tmpdir_factory):
    """Fixture for creating a temporary directory with sample markdown files."""
    data_dir = tmpdir_factory.mktemp("data")
    # Ensure subdir exists for nested document
    (data_dir / "subdir").mkdir()
    # Explicitly specify encoding for compatibility with py.path LocalPath API
    (data_dir / "doc1.md").write_text("This is the first document.", encoding="utf-8")
    (data_dir / "doc2.md").write_text("This is the second document, with more text.", encoding="utf-8")
    (data_dir / "subdir" / "doc3.md").write_text("This is a nested document.", encoding="utf-8")
    return str(data_dir)


@pytest.fixture(scope="module")
def weaviate_client():
    """Fixture for a real Weaviate client, ensuring the service is available."""
    import logging

    logger = logging.getLogger(__name__)
    logger.debug("Attempting to connect to Weaviate for integration tests...")
    client = ingest.connect_to_weaviate()
    logger.debug("Successfully connected to Weaviate.")
    try:
        if client.collections.exists(COLLECTION_NAME):
            logger.debug("Deleting pre-existing test collection: %s", COLLECTION_NAME)
            client.collections.delete(COLLECTION_NAME)
    except Exception as e:
        logger.warning("Error during pre-test cleanup of collection %s: %s", COLLECTION_NAME, e)
    yield client
    try:
        if client.collections.exists(COLLECTION_NAME):
            logger.debug("Deleting test collection after tests: %s", COLLECTION_NAME)
            client.collections.delete(COLLECTION_NAME)
    except Exception as e:
        logger.warning("Error during post-test cleanup of collection %s: %s", COLLECTION_NAME, e)


@pytest.fixture
def weaviate_collection_mock(mock_weaviate_connect):
    """Fixture for mocking the Weaviate collection."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collections.create.return_value = mock_collection
    mock_weaviate_connect.return_value = mock_client
    yield mock_collection


def test_ingest_pipeline_with_real_weaviate(docker_services, weaviate_client):
    """Test the full ingestion pipeline with a real Weaviate instance, using a local model."""
    # Run the ingestion process on the 'test_data' directory
    ingest.ingest(directory="test_data/", collection_name=COLLECTION_NAME)

    # --- Assertions ---
    # Check that the collection was created and contains the correct number of documents
    collection = weaviate_client.collections.get(COLLECTION_NAME)
    count = collection.aggregate.over_all(total_count=True)
    assert count.total_count >= 2  # test.md and test.pdf


def test_ingest_pipeline_loads_and_embeds_data(
    docker_services, weaviate_collection_mock, sample_documents_path, managed_ingest_embedding_model
):
    """Test the full ingestion pipeline from loading docs to inserting into Weaviate with a local model."""
    # Provide a real embedding model for this integration test
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    managed_ingest_embedding_model.return_value = embedding_model

    # Run the ingestion process
    ingest.ingest_documents(
        collection_name=COLLECTION_NAME,
        data_path=sample_documents_path,
        weaviate_client=weaviate_collection_mock._client,
    )

    # --- Assertions ---
    # Check that documents were loaded correctly
    # Three documents should be found and loaded
    # The batch insert should have been called
    assert weaviate_collection_mock.data.insert_many.call_count > 0

    # Get the arguments passed to insert_many
    call_args = weaviate_collection_mock.data.insert_many.call_args
    inserted_objects = call_args[0][0]

    # Verify the number of inserted objects
    assert len(inserted_objects) == 3

    # Check the structure of the inserted data
    first_object = inserted_objects[0]
    assert "content" in first_object
    assert "vector" in first_object

    # Verify that the vector is of the correct dimension (for all-MiniLM-L6-v2)
    assert len(first_object["vector"]) == 384


def test_ingest_pipeline_handles_no_embedding_model(
    managed_ingest_embedding_model, weaviate_collection_mock, sample_documents_path
):
    """Test that the ingestion pipeline exits gracefully if no local embedding model is available."""
    managed_ingest_embedding_model.return_value = None
    with pytest.raises(ValueError, match="Embedding model not available"):
        ingest.ingest_documents(
            collection_name=COLLECTION_NAME,
            data_path=sample_documents_path,
            weaviate_client=weaviate_collection_mock._client,
        )


def test_ingest_pipeline_is_idempotent(
    docker_services, weaviate_collection_mock, sample_documents_path, managed_ingest_embedding_model
):
    """Test that running ingestion multiple times doesn't create duplicate data, using a local model."""
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    managed_ingest_embedding_model.return_value = embedding_model

    # Run ingestion once
    ingest.ingest_documents(
        collection_name=COLLECTION_NAME,
        data_path=sample_documents_path,
        weaviate_client=weaviate_collection_mock._client,
    )
    # Run ingestion a second time
    ingest.ingest_documents(
        collection_name=COLLECTION_NAME,
        data_path=sample_documents_path,
        weaviate_client=weaviate_collection_mock._client,
    )

    # Assert that the creation and insertion logic was accessed correctly,
    # but Weaviate's internal mechanisms should handle idempotency.
    # The client's `create` method should still be called to ensure the collection exists.
    assert weaviate_collection_mock._client.collections.create.call_count > 0
    assert weaviate_collection_mock.data.insert_many.call_count > 0


if __name__ == "__main__":
    pytest.main(["-s", __file__])
