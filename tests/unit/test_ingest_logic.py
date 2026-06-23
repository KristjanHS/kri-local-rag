import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from backend.ingest import (
    _is_valid_pdf,
    deterministic_uuid,
    load_and_split_documents,
    process_and_upload_chunks,
)


def test_is_valid_pdf_accepts_real_magic_bytes(tmp_path):
    """A file starting with the PDF magic bytes is accepted."""
    pdf = tmp_path / "good.pdf"
    pdf.write_bytes(b"%PDF-1.7\n...rest...")
    assert _is_valid_pdf(str(pdf)) is True


def test_is_valid_pdf_rejects_bad_magic_bytes(tmp_path):
    """A non-PDF payload renamed to .pdf is rejected by the magic-byte guard."""
    fake = tmp_path / "evil.pdf"
    fake.write_bytes(b"<html><script>alert(1)</script>")
    assert _is_valid_pdf(str(fake)) is False


def test_is_valid_pdf_rejects_unreadable_file(tmp_path):
    """A path that cannot be opened returns False rather than raising."""
    assert _is_valid_pdf(str(tmp_path / "nope.pdf")) is False


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


def test_load_and_split_documents(tmp_path):
    """Real temp .md + .pdf files are loaded (no loader mock) and split into chunks."""
    # Arrange: a markdown file long enough to force splitting, plus the PDF fixture.
    fixture_pdf = Path(__file__).resolve().parents[1] / "test_data" / "test.pdf"
    shutil.copyfile(fixture_pdf, tmp_path / "doc.pdf")
    (tmp_path / "notes.md").write_text("Markdown content repeated. " * 200, encoding="utf-8")

    # Act
    chunked_docs = load_and_split_documents(str(tmp_path))

    # Assert: splitting occurred and both sources contributed.
    assert len(chunked_docs) > 2
    combined = " ".join(d.page_content for d in chunked_docs)
    assert "Markdown content" in combined
    sources = {Path(str(d.metadata.get("source", ""))).name for d in chunked_docs}
    assert {"doc.pdf", "notes.md"} <= sources


def test_deterministic_uuid(mock_docs):
    """Test that the UUID generation is deterministic."""
    # Act
    uuid1 = deterministic_uuid(mock_docs[0])
    uuid2 = deterministic_uuid(mock_docs[0])  # Same document
    uuid3 = deterministic_uuid(mock_docs[1])  # Different document

    # Assert
    assert uuid1 == uuid2
    assert uuid1 != uuid3


def test_batch_upload_is_used(mock_docs):
    """Verifies that the batch upload context manager is used."""
    # Arrange
    mock_client = MagicMock()
    mock_collection = mock_client.collections.get.return_value
    # The new mock target
    mock_batch_cm = mock_collection.batch.fixed_size.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm
    mock_model = MagicMock()

    # Act
    process_and_upload_chunks(mock_client, mock_docs, mock_model, "test_collection")

    # Assert
    assert mock_collection.batch.fixed_size.call_count == 1
    assert mock_batch_cm.__enter__.called


def test_object_properties_are_correct(mock_docs):
    """Verifies that the object properties are correctly extracted from the documents."""
    # Arrange
    mock_client = MagicMock()
    mock_collection = mock_client.collections.get.return_value
    mock_batch_cm = mock_collection.batch.fixed_size.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]

    # Act
    process_and_upload_chunks(mock_client, mock_docs, mock_model, "test_collection")

    # Assert
    # Check the calls to add_object made on the context manager
    call_list = mock_batch_cm.add_object.call_args_list
    assert len(call_list) == 2, "add_object should be called for each document"

    first_call_kwargs = call_list[0].kwargs
    assert "content" in first_call_kwargs["properties"]
    assert first_call_kwargs["properties"]["source_file"] == "test.pdf"

    second_call_kwargs = call_list[1].kwargs
    assert second_call_kwargs["properties"]["source_file"] == "test.md"


def test_vectors_are_generated_and_added(mock_docs):
    """Verifies that the model is called to generate vectors and that they are added to the batch."""
    # Arrange
    mock_client = MagicMock()
    mock_collection = mock_client.collections.get.return_value
    mock_batch_cm = mock_collection.batch.fixed_size.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]

    # Act
    process_and_upload_chunks(mock_client, mock_docs, mock_model, "test_collection")

    # Assert
    assert mock_model.encode.call_count == len(mock_docs)
    assert mock_batch_cm.add_object.call_count == len(mock_docs)

    # Check the vector in the first call
    _, first_call_kwargs = mock_batch_cm.add_object.call_args_list[0]
    assert "vector" in first_call_kwargs
    assert first_call_kwargs["vector"] == [0.1, 0.2, 0.3]
