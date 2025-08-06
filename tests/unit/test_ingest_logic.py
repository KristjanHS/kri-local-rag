from unittest.mock import MagicMock, patch

import pytest
from langchain.docstore.document import Document

from backend.ingest import (
    deterministic_uuid,
    load_and_split_documents,
    process_and_upload_chunks,
)


@pytest.fixture
def mock_docs():
    """Fixture to create mock Document objects."""
    doc1 = Document(
        page_content="This is the first sentence.",
        metadata={"source": "test_data/test.pdf"},
    )
    doc2 = Document(
        page_content="This is the second sentence.",
        metadata={"source": "test_data/test.md"},
    )
    return [doc1, doc2]


@patch("backend.ingest.DirectoryLoader")
def test_load_and_split_documents(mock_loader):
    """Test that documents are loaded and split correctly."""
    # Arrange
    mock_instance = mock_loader.return_value
    mock_instance.load.return_value = [
        Document(page_content="PDF content repeated. " * 50),
        Document(page_content="Markdown content repeated. " * 50),
    ]

    # Act
    chunked_docs = load_and_split_documents("fake_dir")

    # Assert
    assert len(chunked_docs) > 2  # Check that splitting occurred
    assert "PDF content" in chunked_docs[0].page_content
    assert "Markdown content" in chunked_docs[-1].page_content


def test_deterministic_uuid(mock_docs):
    """Test that the UUID generation is deterministic."""
    # Act
    uuid1 = deterministic_uuid(mock_docs[0])
    uuid2 = deterministic_uuid(mock_docs[0])  # Same document
    uuid3 = deterministic_uuid(mock_docs[1])  # Different document

    # Assert
    assert uuid1 == uuid2
    assert uuid1 != uuid3


@patch("backend.ingest.weaviate")
def test_batch_upload_is_used(mock_weaviate, mock_docs):
    """Verifies that the batch upload context manager is used."""
    # Arrange
    mock_client = mock_weaviate.connect_to_custom.return_value
    mock_collection = mock_client.collections.get.return_value
    mock_batch_cm = mock_collection.batch.dynamic.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm
    mock_model = MagicMock()

    # Act
    process_and_upload_chunks(mock_client, mock_docs, mock_model)

    # Assert
    assert mock_batch_cm.__enter__.called
    assert mock_collection.batch.dynamic.call_count == 1


@patch("backend.ingest.weaviate")
def test_object_properties_are_correct(mock_weaviate, mock_docs):
    """Verifies that the object properties are correctly extracted from the documents."""
    # Arrange
    mock_client = mock_weaviate.connect_to_custom.return_value
    mock_collection = mock_client.collections.get.return_value
    mock_batch_cm = mock_collection.batch.dynamic.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]

    # Act
    process_and_upload_chunks(mock_client, mock_docs, mock_model)

    # Assert
    _, first_call_kwargs = mock_batch_cm.add_object.call_args_list[0]
    assert "content" in first_call_kwargs["properties"]
    assert first_call_kwargs["properties"]["source_file"] == "test.pdf"

    _, second_call_kwargs = mock_batch_cm.add_object.call_args_list[1]
    assert second_call_kwargs["properties"]["source_file"] == "test.md"


@patch("backend.ingest.weaviate")
def test_vectors_are_generated_and_added(mock_weaviate, mock_docs):
    """Verifies that the model is called to generate vectors and that they are added to the batch."""
    # Arrange
    mock_client = mock_weaviate.connect_to_custom.return_value
    mock_collection = mock_client.collections.get.return_value
    mock_batch_cm = mock_collection.batch.dynamic.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]

    # Act
    process_and_upload_chunks(mock_client, mock_docs, mock_model)

    # Assert
    assert mock_model.encode.call_count == len(mock_docs)
    assert mock_batch_cm.add_object.call_count == len(mock_docs)
    _, first_call_kwargs = mock_batch_cm.add_object.call_args_list[0]
    assert "vector" in first_call_kwargs
    assert first_call_kwargs["vector"] == [0.1, 0.2, 0.3]
