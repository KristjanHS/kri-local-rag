#!/usr/bin/env python3
"""Test to verify hybrid search works with manual vectorization."""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from retriever import get_top_k, _get_embedding_model


class TestHybridSearchFix:
    """Test hybrid search with manual vectorization."""

    def test_embedding_model_loading(self):
        """Test that embedding model can be loaded."""
        # Reset the global cache
        import retriever

        retriever._embedding_model = None

        # Test with available SentenceTransformer
        with patch("retriever.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_st.return_value = mock_model

            model = _get_embedding_model()
            assert model is not None
            mock_st.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")

    def test_embedding_model_caching(self):
        """Test that embedding model is cached after first load."""
        import retriever

        retriever._embedding_model = None

        with patch("retriever.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_st.return_value = mock_model

            # First call should create model
            model1 = _get_embedding_model()
            # Second call should return cached model
            model2 = _get_embedding_model()

            assert model1 is model2
            mock_st.assert_called_once()  # Should only be called once due to caching

    def test_embedding_model_unavailable(self):
        """Test behavior when SentenceTransformer is not available."""
        import retriever

        retriever._embedding_model = None
        original_st = retriever.SentenceTransformer

        try:
            # Simulate SentenceTransformer not being available
            retriever.SentenceTransformer = None
            model = _get_embedding_model()
            assert model is None
        finally:
            retriever.SentenceTransformer = original_st

    @patch("retriever.weaviate.connect_to_custom")
    @patch("retriever._get_embedding_model")
    def test_hybrid_search_with_manual_vectorization(self, mock_get_model, mock_connect):
        """Test hybrid search with manual vectorization."""
        # Setup mocks
        mock_model = MagicMock()
        mock_vector = [0.1, 0.2, 0.3]  # Mock embedding vector
        mock_model.encode.return_value = mock_vector
        mock_get_model.return_value = mock_model

        # Mock Weaviate client and collection
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()

        # Mock objects with content - use simple objects instead of MagicMock for comparison
        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_obj1 = MockObject("Test content 1")
        mock_obj2 = MockObject("Test content 2")
        mock_result.objects = [mock_obj1, mock_obj2]

        # Chain the mocks
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.hybrid.return_value = mock_result

        # Test the function
        question = "test question"
        result = get_top_k(question, k=5)

        # Verify embedding model was called
        mock_get_model.assert_called_once()
        mock_model.encode.assert_called_once_with(question)

        # Verify hybrid search was called with vector
        mock_query.hybrid.assert_called_once_with(
            vector=mock_vector,
            query=question,
            alpha=0.5,  # DEFAULT_HYBRID_ALPHA from config
            limit=5,
        )

        # Verify result
        assert result == ["Test content 1", "Test content 2"]

        # Verify client cleanup
        mock_client.close.assert_called_once()

    @patch("retriever.weaviate.connect_to_custom")
    @patch("retriever._get_embedding_model")
    def test_hybrid_search_fallback_to_bm25(self, mock_get_model, mock_connect):
        """Test fallback to BM25 when hybrid search fails."""
        # Setup mocks
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        # Mock Weaviate client and collection
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_bm25_result = MagicMock()

        # Mock hybrid search failure and BM25 success
        from weaviate.exceptions import WeaviateQueryError

        mock_query.hybrid.side_effect = WeaviateQueryError("VectorFromInput was called without vectorizer", "GRPC")

        # Mock BM25 result - use simple object instead of MagicMock for comparison
        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_obj = MockObject("BM25 result")
        mock_bm25_result.objects = [mock_obj]
        mock_query.bm25.return_value = mock_bm25_result

        # Chain the mocks
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query

        # Test the function
        question = "test question"
        result = get_top_k(question, k=5)

        # Verify BM25 was called as fallback
        mock_query.bm25.assert_called_once_with(query=question, limit=5)

        # Verify result from BM25
        assert result == ["BM25 result"]


if __name__ == "__main__":
    pytest.main([__file__])
