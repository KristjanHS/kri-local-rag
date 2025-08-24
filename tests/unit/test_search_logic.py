#!/usr/bin/env python3
"""Test to verify hybrid search works with manual vectorization."""

import os
from unittest.mock import MagicMock

import pytest

# Disable torch.compile during these mocked tests to avoid unnecessary compile overhead
os.environ["RETRIEVER_EMBEDDING_TORCH_COMPILE"] = "false"


class TestHybridSearchFix:
    """Test hybrid search with manual vectorization and error scenarios."""

    def test_embedding_model_loading(self, mock_embedding_model: MagicMock):
        """Test that embedding model can be loaded."""
        from backend.retriever import _get_embedding_model

        # The mock_embedding_model fixture provides the mock automatically
        model = _get_embedding_model()

        assert model is not None
        assert model is mock_embedding_model  # Should return our mock

    def test_embedding_model_caching(self, mock_embedding_model: MagicMock):
        """Test that embedding model is cached after first load."""
        from backend.retriever import _get_embedding_model

        # The mock_embedding_model fixture provides the mock automatically
        model1 = _get_embedding_model()
        model2 = _get_embedding_model()

        assert model1 is model2  # Should return the same cached mock
        assert model1 is mock_embedding_model  # Should be our mock

    def test_embedding_model_unavailable(self, mocker):
        """Test behavior when SentenceTransformer is not available."""
        from backend import retriever

        # Use mocker to patch load_embedder to return None (modern approach)
        mocker.patch("backend.retriever.load_embedder", return_value=None)

        model = retriever._get_embedding_model()
        assert model is None

    def test_retrieval_uses_local_embedding_model(self, mocker, mock_embedding_model: MagicMock):
        """Test that the retriever uses the local embedding model to create a query vector.
        This test will FAIL if hybrid search fails - no graceful fallback allowed."""
        from backend.retriever import get_top_k

        # The mock_embedding_model fixture already provides a mock that will be returned by load_embedder
        # Set up the mock to return the expected vector
        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        mock_embedding_model.encode.return_value = mock_array

        # Use mocker fixture for weaviate mocking (modern approach)
        mock_connect = mocker.patch("backend.retriever.weaviate.connect_to_custom")
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

        # Check that the mock was used and encode was called
        mock_embedding_model.encode.assert_called_once_with(question)

        # CRITICAL: Verify hybrid search was called with correct parameters
        mock_query.hybrid.assert_called_once_with(
            vector=[0.1, 0.2, 0.3],
            query=question,
            alpha=0.5,
            limit=5,
        )

        # CRITICAL: Verify BM25 was NEVER called (hybrid search must succeed)
        mock_query.bm25.assert_not_called()

        assert result == ["Test content 1", "Test content 2"]
        mock_client.close.assert_called_once()

    def test_hybrid_search_fallback_to_bm25(self, mocker, mock_embedding_model: MagicMock):
        """Test fallback to BM25 when hybrid search fails."""
        from weaviate.exceptions import WeaviateQueryError

        from backend.retriever import get_top_k

        # Use mocker fixture for weaviate mocking (modern approach)
        mock_connect = mocker.patch("backend.retriever.weaviate.connect_to_custom")
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

    def test_hybrid_search_with_empty_collection(self, mocker, mock_embedding_model: MagicMock):
        """Test hybrid search behavior with empty collection."""
        from backend.retriever import get_top_k

        # Use mocker fixture for weaviate mocking (modern approach)
        mock_connect = mocker.patch("backend.retriever.weaviate.connect_to_custom")
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

    def test_vectorization_error_scenario(self, mocker):
        """Test behavior when vectorization fails."""
        from backend.retriever import _get_embedding_model

        # Use mocker to patch load_embedder to return None (modern approach)
        # The autouse fixture already reset the cache, so this should work
        mocker.patch("backend.retriever.load_embedder", return_value=None)

        model = _get_embedding_model()
        assert model is None

    def test_hybrid_search_without_embedding_model(self, mocker, mock_embedding_model: MagicMock):
        """Verify hybrid search works even when loader returns None by passing model explicitly.
        Ensures no fallback is used."""
        from backend.retriever import get_top_k

        # Simulate loader unavailability but provide model explicitly
        mocker.patch("backend.retriever.load_embedder", return_value=None)

        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        mock_embedding_model.encode.return_value = mock_array

        mock_connect = mocker.patch("backend.retriever.weaviate.connect_to_custom")
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_result.objects = [MockObject("Fallback must not be used")]

        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.hybrid.return_value = mock_result

        result = get_top_k("test question", k=1, embedding_model=mock_embedding_model)

        mock_query.hybrid.assert_called_once_with(vector=[0.1, 0.2, 0.3], query="test question", alpha=0.5, limit=1)
        mock_query.bm25.assert_not_called()
        assert result == ["Fallback must not be used"]

    def test_hybrid_search_fallback_to_bm25_when_no_embedding_model(self, mocker):
        """Test hybrid search falls back to BM25 when no embedding model is available."""
        from weaviate.exceptions import WeaviateQueryError

        from backend.retriever import get_top_k

        # Use mocker to patch load_embedder to return None (modern approach)
        mocker.patch("backend.retriever.load_embedder", return_value=None)

        # Use mocker fixture for weaviate mocking (modern approach)
        mock_connect = mocker.patch("backend.retriever.weaviate.connect_to_custom")
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


class TestHybridSearchFailureDetection:
    pass


if __name__ == "__main__":
    pytest.main([__file__])
