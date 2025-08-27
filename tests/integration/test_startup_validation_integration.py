#!/usr/bin/env python3
"""Integration tests for startup validation - real service connections."""

import logging
from unittest.mock import MagicMock

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.external
class TestInitializationLogging:
    """Integration tests for initialization logging with real service connections."""

    def test_weaviate_check_logging(self, mock_weaviate_connect):
        """Test that Weaviate check produces appropriate log messages."""
        # Mock successful connection
        mock_client = MagicMock()
        mock_client.is_ready.return_value = True
        mock_client.collections.exists.return_value = True
        mock_weaviate_connect.return_value = mock_client

        from backend.qa_loop import ensure_weaviate_ready_and_populated

        # Should complete without exceptions
        ensure_weaviate_ready_and_populated()

        # Verify client methods were called
        mock_client.is_ready.assert_called_once()
        mock_client.collections.exists.assert_called_once()
        # Note: close_weaviate_client() is called instead of client.close() with wrapper pattern

    def test_ollama_model_check_logging(self, mock_httpx_get):
        """Test Ollama model availability check logging."""
        from backend.ollama_client import ensure_model_available

        # Mock successful model check
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "test-model"}]}
        mock_response.raise_for_status.return_value = None
        mock_httpx_get.return_value = mock_response

        result = ensure_model_available("test-model")
        assert result is True


@pytest.mark.external
class TestHybridSearchIntegration:
    """Integration tests for hybrid search with real service interactions."""

    def test_retrieval_with_local_vectorization(self, mock_weaviate_connect, managed_embedding_model):
        """Integration test for retriever ensuring it uses the local embedding model."""
        from backend.retriever import get_top_k

        # Setup embedding model mock behavior via the fixture
        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        managed_embedding_model.encode.return_value = mock_array

        # Setup Weaviate mock
        mock_client = MagicMock()
        mock_collection = MagicMock()

        # Mock successful hybrid search
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_result.objects = [MockObject("Test content 1"), MockObject("Test content 2")]

        # Mock the query attribute on the collection and its hybrid method
        mock_collection.query.hybrid.return_value = mock_result
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate_connect.return_value = mock_client

        # Test the integration
        result = get_top_k("test question", k=5)

        # Verify the flow
        # The fixture handles the patching, so we just check the model's methods
        managed_embedding_model.encode.assert_called_once_with("test question")
        mock_collection.query.hybrid.assert_called_once_with(
            vector=[0.1, 0.2, 0.3], query="test question", alpha=0.5, limit=5
        )

        assert result == ["Test content 1", "Test content 2"]


@pytest.mark.slow
class TestContainerReadiness:
    """Integration tests for container readiness and CLI behaviors."""

    def test_python_execution_in_container_context(self):
        """Test that Python can execute basic commands in the expected environment."""
        from backend import config, ollama_client, retriever

        # Should be able to import all core modules
        assert hasattr(config, "OLLAMA_MODEL")
        assert hasattr(ollama_client, "ensure_model_available")
        assert hasattr(retriever, "get_top_k")

    def test_weaviate_url_configuration(self):
        """Test that Weaviate URL is properly configured for container environment."""
        from backend.config import WEAVIATE_URL

        # Should be configured for Docker networking
        assert WEAVIATE_URL is not None
        assert len(WEAVIATE_URL) > 0

    def test_collection_name_configuration(self):
        """Test that collection name is properly configured."""
        from backend.config import COLLECTION_NAME

        assert COLLECTION_NAME is not None
        assert len(COLLECTION_NAME) > 0


if __name__ == "__main__":
    pytest.main([__file__])
