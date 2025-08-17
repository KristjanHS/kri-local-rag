#!/usr/bin/env python3
"""Test to verify hybrid search works with manual vectorization."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Disable torch.compile during these mocked tests to avoid unnecessary compile overhead
os.environ["RETRIEVER_EMBEDDING_TORCH_COMPILE"] = "false"

pytestmark = pytest.mark.unit


class TestHybridSearchFix:
    """Test hybrid search with manual vectorization and error scenarios."""

    def test_embedding_model_loading(self, mock_embedding_model: MagicMock):
        """Test that embedding model can be loaded."""
        from backend import retriever
        from backend.retriever import _get_embedding_model

        retriever._embedding_model = None  # Ensure clean state

        mock_model_instance = MagicMock()
        mock_embedding_model.return_value = mock_model_instance

        model = _get_embedding_model()

        assert model is not None
        mock_embedding_model.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")

    def test_embedding_model_caching(self, mock_embedding_model: MagicMock):
        """Test that embedding model is cached after first load."""
        from backend import retriever
        from backend.retriever import _get_embedding_model

        retriever._embedding_model = None  # Ensure clean state

        mock_model_instance = MagicMock()
        mock_embedding_model.return_value = mock_model_instance

        model1 = _get_embedding_model()
        model2 = _get_embedding_model()

        assert model1 is model2
        mock_embedding_model.assert_called_once()

    def test_embedding_model_unavailable(self, monkeypatch: pytest.MonkeyPatch):
        """Test behavior when SentenceTransformer is not available."""
        from backend import retriever

        monkeypatch.setattr(retriever, "SentenceTransformer", None)
        retriever._embedding_model = None  # Ensure clean state

        model = retriever._get_embedding_model()
        assert model is None

    @patch("backend.retriever.weaviate.connect_to_custom")
    def test_retrieval_uses_local_embedding_model(self, mock_connect: MagicMock, mock_embedding_model: MagicMock):
        """Test that the retriever uses the local embedding model to create a query vector."""
        from backend.retriever import get_top_k
        from backend import retriever

        retriever._embedding_model = None  # Ensure clean state

        mock_model_instance = MagicMock()
        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model_instance.encode.return_value = mock_array
        mock_embedding_model.return_value = mock_model_instance

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_obj1 = MockObject("Test content 1")
        mock_obj2 = MockObject("Test content 2")
        mock_result.objects = [mock_obj1, mock_obj2]

        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.hybrid.return_value = mock_result

        question = "test question"
        result = get_top_k(question, k=5)

        mock_embedding_model.assert_called_once()
        mock_model_instance.encode.assert_called_once_with(question)

        mock_query.hybrid.assert_called_once_with(
            vector=[0.1, 0.2, 0.3],
            query=question,
            alpha=0.5,
            limit=5,
        )

        assert result == ["Test content 1", "Test content 2"]
        mock_client.close.assert_called_once()

    @patch("backend.retriever.weaviate.connect_to_custom")
    def test_hybrid_search_fallback_to_bm25(self, mock_connect: MagicMock, mock_embedding_model: MagicMock):
        """Test fallback to BM25 when hybrid search fails."""
        from backend.retriever import get_top_k
        from backend import retriever
        from weaviate.exceptions import WeaviateQueryError

        retriever._embedding_model = None  # Ensure clean state

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_bm25_result = MagicMock()

        mock_query.hybrid.side_effect = WeaviateQueryError("VectorFromInput was called without vectorizer", "GRPC")

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_obj = MockObject("BM25 result")
        mock_bm25_result.objects = [mock_obj]
        mock_query.bm25.return_value = mock_bm25_result

        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query

        question = "test question"
        result = get_top_k(question, k=5)

        mock_query.bm25.assert_called_once_with(query=question, limit=5)
        assert result == ["BM25 result"]

    @patch("backend.retriever.weaviate.connect_to_custom")
    def test_hybrid_search_with_empty_collection(self, mock_connect: MagicMock, mock_embedding_model: MagicMock):
        """Test hybrid search behavior with empty collection."""
        from backend.retriever import get_top_k
        from backend import retriever

        retriever._embedding_model = None  # Ensure clean state

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.objects = []

        mock_query.hybrid.return_value = mock_result
        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection
        mock_connect.return_value = mock_client

        result = get_top_k("test question", k=5)

        assert result == []

    def test_vectorization_error_scenario(self, monkeypatch: pytest.MonkeyPatch):
        """Test behavior when vectorization fails."""
        from backend import retriever
        import importlib

        monkeypatch.setattr(retriever, "SentenceTransformer", None)
        retriever._embedding_model = None  # Ensure clean state
        importlib.reload(retriever)

        model = retriever._get_embedding_model()
        assert model is None

    @patch("backend.retriever.weaviate.connect_to_custom")
    def test_hybrid_search_without_embedding_model(self, mock_connect: MagicMock, monkeypatch: pytest.MonkeyPatch):
        """Test hybrid search falls back when no embedding model is available."""
        from backend.retriever import get_top_k
        from backend import retriever
        from weaviate.exceptions import WeaviateQueryError

        monkeypatch.setattr(retriever, "SentenceTransformer", None)
        retriever._embedding_model = None  # Ensure clean state

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_result.objects = [MockObject("Fallback content")]

        mock_query.hybrid.side_effect = WeaviateQueryError("No vectorizer", "GRPC")
        mock_query.bm25.return_value = mock_result

        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection
        mock_connect.return_value = mock_client

        result = get_top_k("test question", k=1)

        mock_query.bm25.assert_called_once()
        assert result == ["Fallback content"]


if __name__ == "__main__":
    pytest.main([__file__])
