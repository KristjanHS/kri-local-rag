#!/usr/bin/env python3
"""Test to verify hybrid search works with manual vectorization."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Disable torch.compile during these mocked tests to avoid unnecessary compile overhead
os.environ["RETRIEVER_EMBEDDING_TORCH_COMPILE"] = "false"

pytestmark = pytest.mark.unit

# Mock sentence_transformers at module level to prevent real imports
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["sentence_transformers"].SentenceTransformer = MagicMock()

# Note: The main 'from retriever import ...' is moved inside the test functions
# to prevent hanging during pytest collection.


class TestHybridSearchFix:
    """Test hybrid search with manual vectorization and error scenarios."""

    def setup_method(self):
        """Reset global state before each test to ensure isolation."""
        # Import here to avoid module-level import issues
        from backend import retriever

        # Reset all global state that could interfere between tests
        retriever._embedding_model = None
        retriever.SentenceTransformer = None

    @patch("backend.retriever.SentenceTransformer")
    def test_embedding_model_loading(self, mock_st):
        """Test that embedding model can be loaded."""
        # Import inside test to ensure fresh state
        from backend import retriever
        from backend.retriever import _get_embedding_model

        # Ensure clean state
        retriever._embedding_model = None
        retriever.SentenceTransformer = None

        # Mock SentenceTransformer
        mock_model_instance = MagicMock()
        mock_st.return_value = mock_model_instance

        # Set the module-level SentenceTransformer to our mock
        retriever.SentenceTransformer = mock_st

        # Test loading
        model = _get_embedding_model()

        assert model is not None
        mock_st.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")

    @patch("backend.retriever.SentenceTransformer")
    def test_embedding_model_caching(self, mock_st):
        """Test that embedding model is cached after first load."""
        from backend import retriever
        from backend.retriever import _get_embedding_model

        # Ensure clean state
        retriever._embedding_model = None
        retriever.SentenceTransformer = None

        mock_model_instance = MagicMock()
        mock_st.return_value = mock_model_instance

        # Set the module-level SentenceTransformer to our mock
        retriever.SentenceTransformer = mock_st

        # First call should create model
        model1 = _get_embedding_model()
        # Second call should return cached model
        model2 = _get_embedding_model()

        assert model1 is model2
        mock_st.assert_called_once()  # Should only be called once due to caching

    def test_embedding_model_unavailable(self):
        """Test behavior when SentenceTransformer is not available."""
        from backend import retriever

        # Ensure clean state
        retriever._embedding_model = None
        retriever.SentenceTransformer = None

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            model = retriever._get_embedding_model()
            assert model is None

    @patch("backend.retriever.weaviate.connect_to_custom")
    @patch("backend.retriever._get_embedding_model")
    def test_retrieval_uses_local_embedding_model(self, mock_get_model, mock_connect):
        """Test that the retriever uses the local embedding model to create a query vector."""
        from backend.retriever import get_top_k

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

    @patch("backend.retriever.weaviate.connect_to_custom")
    @patch("backend.retriever._get_embedding_model")
    def test_hybrid_search_fallback_to_bm25(self, mock_get_model, mock_connect):
        """Test fallback to BM25 when hybrid search fails."""
        from backend.retriever import get_top_k

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

    @patch("backend.retriever.weaviate.connect_to_custom")
    @patch("backend.retriever._get_embedding_model")
    def test_hybrid_search_with_empty_collection(self, mock_get_model, mock_connect):
        """Test hybrid search behavior with empty collection."""
        from backend.retriever import get_top_k

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

    def test_vectorization_error_scenario(self):
        """Test behavior when vectorization fails."""
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            import importlib

            from backend import retriever

            importlib.reload(retriever)
            model = retriever._get_embedding_model()
            assert model is None

    @patch("backend.retriever.weaviate.connect_to_custom")
    def test_hybrid_search_without_embedding_model(self, mock_connect):
        """Test hybrid search falls back when no embedding model is available."""
        from backend.retriever import get_top_k

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
        with patch("backend.retriever._get_embedding_model", return_value=None):
            result = get_top_k("test question", k=1)

            # Should fall back to BM25
            mock_query.bm25.assert_called_once()
            assert result == ["Fallback content"]


if __name__ == "__main__":
    pytest.main([__file__])
