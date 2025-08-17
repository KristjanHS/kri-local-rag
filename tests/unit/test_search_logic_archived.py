#!/usr/bin/env python3
"""Archived tests for search logic - not run as part of the main suite."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock sentence_transformers at module level to prevent real imports
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["sentence_transformers"].SentenceTransformer = MagicMock()


class TestArchivedHybridSearch:
    """Archived tests for hybrid search with manual vectorization and error scenarios."""

    @pytest.mark.skip(reason="Incomplete test with no assertions")
    @patch("backend.retriever.weaviate.connect_to_custom")
    @patch("backend.retriever._get_embedding_model")
    def test_hybrid_search_connection_error_handling(self, mock_get_model, mock_connect):
        """Test hybrid search handles connection errors gracefully."""
        # Setup embedding model mock
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        # Mock connection failure
        mock_connect.side_effect = Exception("Connection failed")

        # Should handle the error gracefully

    @pytest.mark.skip(reason="Does not test logging and functionality is redundant")
    @patch("backend.retriever.weaviate.connect_to_custom")
    @patch("backend.retriever._get_embedding_model")
    def test_chunk_head_logging_at_info_level(self, mock_get_model, mock_connect):
        """Test that chunk heads are logged at INFO level for visibility."""
        from backend.retriever import get_top_k

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
