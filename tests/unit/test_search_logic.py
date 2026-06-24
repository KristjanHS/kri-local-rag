#!/usr/bin/env python3
"""Test to verify hybrid search works with manual vectorization."""

import os
from unittest.mock import MagicMock

import pytest

# Disable torch.compile during these mocked tests to avoid unnecessary compile overhead
os.environ["RETRIEVER_EMBEDDING_TORCH_COMPILE"] = "false"


class TestHybridSearchFix:
    """Test hybrid search with manual vectorization and error scenarios."""

    def test_embedding_model_unavailable(self, mocker):
        """When the loader returns None, _get_embedding_model returns None (no raise)."""
        from backend import retriever

        mocker.patch("backend.retriever.load_embedder", return_value=None)

        assert retriever._get_embedding_model() is None

    def test_retrieval_uses_local_embedding_model(self, mocker, mock_embedding_model: MagicMock):
        """Retriever vectorizes the query locally and runs hybrid search (no BM25 fallback)."""
        from backend.retriever import get_top_k

        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        mock_embedding_model.encode.return_value = mock_array

        mock_client = MagicMock()
        mocker.patch("backend.weaviate_client.get_weaviate_client", return_value=mock_client)
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_result.objects = [MockObject("Test content 1"), MockObject("Test content 2")]

        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.hybrid.return_value = mock_result

        question = "test question"
        result = get_top_k(question, k=5)

        mock_embedding_model.encode.assert_called_once_with(question)
        mock_query.hybrid.assert_called_once_with(
            vector=[0.1, 0.2, 0.3],
            query=question,
            alpha=0.5,
            limit=5,
        )
        mock_query.bm25.assert_not_called()
        assert result == ["Test content 1", "Test content 2"]

    def test_hybrid_search_with_empty_collection(self, mocker, mock_embedding_model: MagicMock):
        """An empty collection yields an empty result list."""
        from backend.retriever import get_top_k

        mock_client = MagicMock()
        mocker.patch("backend.weaviate_client.get_weaviate_client", return_value=mock_client)
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.objects = []

        mock_query.hybrid.return_value = mock_result
        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection

        result = get_top_k("test question", k=5)

        assert result == []

    @pytest.mark.parametrize("embedding_available", [True, False])
    def test_hybrid_search_failure_raises(self, mocker, mock_embedding_model: MagicMock, embedding_available: bool):
        """A hybrid-query failure raises RuntimeError and never falls back to BM25 —
        whether or not a local embedding model is available."""
        from weaviate.exceptions import WeaviateQueryError

        from backend.retriever import get_top_k

        if not embedding_available:
            mocker.patch("backend.retriever.load_embedder", return_value=None)

        mock_client = MagicMock()
        mocker.patch("backend.weaviate_client.get_weaviate_client", return_value=mock_client)
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_query.hybrid.side_effect = WeaviateQueryError("VectorFromInput was called without vectorizer", "GRPC")
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query

        with pytest.raises(RuntimeError):
            get_top_k("test question", k=5)

        mock_query.bm25.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
