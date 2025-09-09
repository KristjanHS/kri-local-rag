from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from backend.ingest import load_and_split_documents, process_and_upload_chunks


def test_markdown_ingestion_loads_and_uploads(tmp_path: Path):
    # Arrange: create a simple Markdown file
    md_path = tmp_path / "sample.md"
    md_path.write_text(
        "# Title\n\nThis is sample Markdown content for ingestion tests.\n\n- bullet 1\n- bullet 2\n",
        encoding="utf-8",
    )

    # Act: load and split documents from the directory containing the .md
    docs = load_and_split_documents(str(tmp_path))

    # Assert: at least one chunk is produced
    assert docs, "Expected at least one chunk from Markdown ingestion"

    # Arrange: mock a minimal Weaviate client and embedding model
    mock_client = MagicMock()
    mock_collection = mock_client.collections.get.return_value
    mock_batch_cm = mock_collection.batch.fixed_size.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm

    class _MockModel:
        def encode(self, text: str):  # noqa: D401
            # Return a small, stable vector to simulate embeddings
            return [0.1, 0.2, 0.3]

    mock_model = _MockModel()

    # Act: process and upload the produced chunks
    process_and_upload_chunks(mock_client, docs, mock_model, "TestCollection")

    # Assert: upload was called and Markdown metadata normalized
    assert mock_batch_cm.add_object.call_count >= 1
    _, first_kwargs = mock_batch_cm.add_object.call_args
    props = first_kwargs["properties"]
    assert props["source_file"].endswith("sample.md")
    assert props["source"] == "md"  # normalized extension
