#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, List
from unittest.mock import MagicMock

from langchain.docstore.document import Document

from backend.ingest import SupportsEncode, process_and_upload_chunks


class DummyEmbedder:
    """A simple test double that satisfies SupportsEncode."""

    def __init__(self) -> None:
        self.calls: int = 0

    # Match the protocol: first arg is positional-only for compatibility
    def encode(self, text: str, /, *args: Any, **kwargs: Any) -> List[float]:  # pragma: no cover - exercised in test
        self.calls += 1
        # Return a stable, small vector for test purposes
        return [0.1, 0.2, 0.3]


def test_dummy_embedder_conforms_to_protocol() -> None:
    embedder = DummyEmbedder()
    # runtime_checkable allows isinstance checks for Protocols
    assert isinstance(embedder, SupportsEncode)


def test_process_and_upload_with_protocol_impl() -> None:
    # Arrange: mock Weaviate client/collection batch context
    mock_client = MagicMock()
    mock_collection = mock_client.collections.get.return_value
    mock_batch_cm = mock_collection.batch.fixed_size.return_value
    mock_batch_cm.__enter__.return_value = mock_batch_cm

    # Two small documents
    docs = [
        Document(page_content="hello world", metadata={"source": "tests/test_data/a.pdf"}),
        Document(page_content="bye world", metadata={"source": "tests/test_data/b.md"}),
    ]

    embedder = DummyEmbedder()

    # Act
    process_and_upload_chunks(mock_client, docs, embedder, "test_collection")

    # Assert: embedder was used and batch add_object called per doc
    assert embedder.calls == len(docs)
    assert mock_collection.batch.fixed_size.call_count == 1
    assert mock_batch_cm.add_object.call_count == len(docs)

    # Check that vectors from the embedder are passed through
    _, first_kwargs = mock_batch_cm.add_object.call_args_list[0]
    assert first_kwargs["vector"] == [0.1, 0.2, 0.3]
