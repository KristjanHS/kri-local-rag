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
        metadata={"source": "/app/data/test.pdf"},
    )
    doc2 = Document(
        page_content="This is the second sentence.",
        metadata={"source": "/app/data/test.md"},
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
def test_process_and_upload_chunks(mock_weaviate, mock_docs):
    """Test the chunk processing and uploading logic."""
    # Arrange
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collections.get.return_value = mock_collection

    mock_batch = MagicMock()
    mock_collection.batch.dynamic.return_value = mock_batch

    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]  # Dummy vector

    # Act
    stats = process_and_upload_chunks(mock_client, mock_docs, mock_model)

    # Assert
    assert mock_batch.__enter__.called  # Check that batch context was used
    assert mock_collection.batch.dynamic.call_count == 1
    assert mock_batch.add_object.call_count == len(mock_docs)

    # Check the properties of the first call
    _, first_call_kwargs = mock_batch.add_object.call_args_list[0]
    assert "content" in first_call_kwargs["properties"]
    assert first_call_kwargs["properties"]["source_file"] == "test.pdf"

    # Check the properties of the second call
    _, second_call_kwargs = mock_batch.add_object.call_args_list[1]
    assert second_call_kwargs["properties"]["source_file"] == "test.md"

    assert stats["inserts"] == len(mock_docs)
