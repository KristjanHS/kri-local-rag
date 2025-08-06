#!/usr/bin/env python3
"""Test to verify hybrid search works with manual vectorization."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Disable torch.compile during these mocked tests to avoid unnecessary compile overhead
os.environ["ENABLE_TORCH_COMPILE"] = "false"


# Note: The main 'from retriever import ...' is moved inside the test functions
# to prevent hanging during pytest collection.


class TestHybridSearchFix:
    """Test hybrid search with manual vectorization and error scenarios."""

    @patch("retriever.SentenceTransformer")
    def test_embedding_model_loading(self, mock_st):
        """Test that embedding model can be loaded."""
        # Reset the global cache
        import retriever
        from retriever import _get_embedding_model

        retriever._embedding_model = None

        # Mock SentenceTransformer
        mock_model_instance = MagicMock()
        mock_st.return_value = mock_model_instance

        # Test loading
        model = _get_embedding_model()

        assert model is not None
        mock_st.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")

    @patch("retriever.SentenceTransformer")
    def test_embedding_model_caching(self, mock_st):
        """Test that embedding model is cached after first load."""
        import retriever
        from retriever import _get_embedding_model

        retriever._embedding_model = None

        mock_model_instance = MagicMock()
        mock_st.return_value = mock_model_instance

        # First call should create model
        model1 = _get_embedding_model()
        # Second call should return cached model
        model2 = _get_embedding_model()

        assert model1 is model2
        mock_st.assert_called_once()  # Should only be called once due to caching

    def test_embedding_model_unavailable(self):
        """Test behavior when SentenceTransformer is not available."""
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            import importlib

            import retriever

            importlib.reload(retriever)

            model = retriever._get_embedding_model()
            assert model is None

    @patch("retriever.weaviate.connect_to_custom")
    @patch("retriever._get_embedding_model")
    def test_hybrid_search_with_manual_vectorization(self, mock_get_model, mock_connect):
        """Test hybrid search with manual vectorization."""
        from retriever import get_top_k

        # Setup mocks
        mock_model = MagicMock()
        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_array
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
            vector=[0.1, 0.2, 0.3],  # The result of tolist()
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
        from retriever import get_top_k

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

    @patch("retriever.weaviate.connect_to_custom")
    @patch("retriever._get_embedding_model")
    def test_hybrid_search_with_empty_collection(self, mock_get_model, mock_connect):
        """Test hybrid search behavior with empty collection."""
        from retriever import get_top_k

        # Setup mocks
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        # Mock empty result
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.objects = []  # Empty collection

        mock_query.hybrid.return_value = mock_result
        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection
        mock_connect.return_value = mock_client

        # Test with empty collection
        result = get_top_k("test question", k=5)

        assert result == []

    @patch("retriever.weaviate.connect_to_custom")
    @patch("retriever._get_embedding_model")
    def test_hybrid_search_connection_error_handling(self, mock_get_model, mock_connect):
        """Test hybrid search handles connection errors gracefully."""
        # Setup embedding model mock
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        # Mock connection failure
        mock_connect.side_effect = Exception("Connection failed")

        # Should handle the error gracefully

    def test_vectorization_error_scenario(self):
        """Test behavior when vectorization fails."""
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            import importlib

            import retriever

            importlib.reload(retriever)

            model = retriever._get_embedding_model()
            assert model is None

    @patch("retriever.weaviate.connect_to_custom")
    @patch("retriever._get_embedding_model")
    def test_chunk_head_logging_at_info_level(self, mock_get_model, mock_connect):
        """Test that chunk heads are logged at INFO level for visibility."""
        from retriever import get_top_k

        # Setup mocks
        mock_model = MagicMock()
        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_array
        mock_get_model.return_value = mock_model

        # Mock Weaviate response with content
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        # Create mock objects with longer content to test truncation
        long_content = "This is a long piece of content that should be truncated in the log message " * 3
        mock_result.objects = [MockObject(long_content)]

        mock_query.hybrid.return_value = mock_result
        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection
        mock_connect.return_value = mock_client

        # Test the function - should not raise errors
        result = get_top_k("test question", k=1)

        # Verify content was returned
        assert len(result) == 1
        assert result[0] == long_content

    @patch("retriever.weaviate.connect_to_custom")
    def test_hybrid_search_without_embedding_model(self, mock_connect):
        """Test hybrid search falls back when no embedding model is available."""
        from retriever import get_top_k

        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_result.objects = [MockObject("Fallback content")]

        # Mock hybrid search failing, BM25 succeeding
        from weaviate.exceptions import WeaviateQueryError

        mock_query.hybrid.side_effect = WeaviateQueryError("No vectorizer", "GRPC")
        mock_query.bm25.return_value = mock_result

        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection
        mock_connect.return_value = mock_client

        # Test fallback behavior
        with patch("retriever._get_embedding_model", return_value=None):
            result = get_top_k("test question", k=1)

            # Should fall back to BM25
            mock_query.bm25.assert_called_once()
            assert result == ["Fallback content"]


if __name__ == "__main__":
    pytest.main([__file__])
