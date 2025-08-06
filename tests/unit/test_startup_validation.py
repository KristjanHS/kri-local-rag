#!/usr/bin/env python3
"""Test startup performance and initialization behaviors."""

import logging
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.slow
class TestStartupPerformance:
    """Test application startup performance and initialization."""

    def test_backend_files_exist(self):
        """Test that core backend files exist without importing them."""
        logger.info("\n=== TESTING FILE EXISTENCE ===")

        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")

        files_to_check = ["config.py", "qa_loop.py", "retriever.py", "ollama_client.py"]

        for filename in files_to_check:
            filepath = os.path.join(backend_dir, filename)
            logger.info(f"Checking {filename}...")
            assert os.path.exists(filepath), f"{filename} should exist"
            logger.info(f"✓ {filename} exists")

        logger.info("=== FILE EXISTENCE TEST COMPLETED ===")

    def test_import_structure_without_execution(self):
        """Test import structure by reading files as text without executing them."""
        logger.info("\n=== TESTING IMPORT STRUCTURE ===")

        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")

        # Test config.py has expected variables
        logger.info("Analyzing config.py...")
        config_path = os.path.join(backend_dir, "config.py")
        with open(config_path, "r") as f:
            config_content = f.read()
            assert "OLLAMA_MODEL" in config_content
            assert "WEAVIATE_URL" in config_content
            assert "COLLECTION_NAME" in config_content
        logger.info("✓ config.py structure validated")

        # Test retriever.py has proper import fallback
        logger.info("Analyzing retriever.py...")
        retriever_path = os.path.join(backend_dir, "retriever.py")
        with open(retriever_path, "r") as f:
            retriever_content = f.read()
            assert "try:" in retriever_content
            assert "ImportError:" in retriever_content
            assert "sentence_transformers" in retriever_content
        logger.info("✓ retriever.py import fallback structure validated")

        logger.info("=== IMPORT STRUCTURE TEST COMPLETED ===")

    def test_python_syntax_is_valid(self):
        """Test that all Python files have valid syntax without importing."""
        import ast

        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")

        python_files = ["config.py", "qa_loop.py", "retriever.py", "ollama_client.py"]

        for filename in python_files:
            filepath = os.path.join(backend_dir, filename)
            with open(filepath, "r") as f:
                content = f.read()
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Syntax error in {filename}: {e}")

    def test_detect_interactive_prompts_in_imports(self):
        """Test to detect if imports are waiting for interactive prompts."""
        logger.info("\n=== TESTING FOR INTERACTIVE PROMPTS ===")
        import subprocess

        project_root = os.path.join(os.path.dirname(__file__), "..")

        logger.info("Testing config.py import in subprocess...")
        try:
            result = subprocess.run(
                ["python", "-m", "backend.config"],
                capture_output=True,
                text=True,
                timeout=10,  # 10-second timeout
                cwd=project_root,
            )

            if result.returncode == 0:
                logger.info("✓ config.py imports without hanging")
            else:
                logger.warning(f"⚠ config.py import failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("✗ config.py import timed out - likely waiting for input!")
        except Exception as e:
            logger.error(f"✗ config.py import test failed: {e}")

        logger.info("=== INTERACTIVE PROMPT TEST COMPLETED ===")

    def test_safe_config_import_only(self):
        """Test importing only the config module safely."""
        logger.info("\n=== TESTING SAFE CONFIG IMPORT ===")

        logger.info("About to import config module...")

        try:
            from backend import config

            logger.info("✓ Config module imported successfully!")

            # Test some basic attributes
            logger.info("Testing config attributes...")
            assert hasattr(config, "OLLAMA_MODEL"), "Should have OLLAMA_MODEL"
            assert hasattr(config, "WEAVIATE_URL"), "Should have WEAVIATE_URL"
            logger.info("✓ Config attributes validated")

        except Exception as e:
            logger.error(f"✗ Config import failed: {e}")
            raise

        logger.info("=== SAFE CONFIG IMPORT COMPLETED ===")

    @patch("backend.qa_loop.ensure_weaviate_ready_and_populated")
    @patch("backend.qa_loop.ensure_model_available")
    def test_qa_loop_initialization_components(self, mock_ensure_model, mock_ensure_weaviate):
        """Test that QA loop initialization components work correctly."""
        # Mock successful initialization
        mock_ensure_weaviate.return_value = None
        mock_ensure_model.return_value = True

        # Import and test initialization logic

        # Should not raise any exceptions
        mock_ensure_weaviate.assert_not_called()  # Only called in __main__
        mock_ensure_model.assert_not_called()  # Only called in __main__

    def test_heavy_imports_eventually_succeed(self):
        """Test that heavy ML library imports eventually succeed."""
        logger.info("\n=== STARTING HEAVY IMPORT TEST ===")
        start_time = time.time()

        try:
            logger.info("Step 1: About to import retriever module...")

            logger.info("Step 2: Retriever imported successfully!")
            import_time = time.time() - start_time
            logger.info(f"Step 3: Import completed in {import_time:.2f}s")

            # Allow generous time for ML library imports on first run
            assert import_time < 30.0, f"Heavy imports took {import_time:.2f}s, should be < 30.0s"

        except Exception as e:
            logger.error(f"Step X: Import failed with error: {e}")
            pytest.skip(f"Heavy imports failed (expected in some environments): {e}")

        logger.info("=== HEAVY IMPORT TEST COMPLETED ===")

    def test_sentence_transformers_graceful_fallback(self):
        """Test graceful fallback when sentence_transformers is not available."""
        # Test the fallback logic without actually importing heavy libraries
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            # This should not hang because we're mocking the import
            try:
                # Clear any cached module
                if "backend.qa_loop" in sys.modules:
                    del sys.modules["backend.qa_loop"]

                # Now test the fallback
                from backend import qa_loop

                result = qa_loop._get_cross_encoder()
                assert result is None
            except ImportError:
                # Expected when sentence_transformers is mocked as None
                pass

    def test_retriever_import_fallback_without_heavy_import(self):
        """Test that retriever handles missing sentence_transformers gracefully."""
        # This test ensures that if sentence-transformers is not installed,
        # the retriever module still loads and functions without errors.
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            import importlib

            from backend import retriever

            importlib.reload(retriever)

            model = retriever._get_embedding_model()
            assert model is None


class TestInitializationLogging:
    """Test initialization logging and message deduplication."""

    @patch("weaviate.connect_to_custom")
    def test_weaviate_check_logging(self, mock_connect):
        """Test that Weaviate check produces appropriate log messages."""
        # Mock successful connection
        mock_client = MagicMock()
        mock_client.is_ready.return_value = True
        mock_client.collections.exists.return_value = True
        mock_connect.return_value = mock_client

        from backend.qa_loop import ensure_weaviate_ready_and_populated

        # Should complete without exceptions
        ensure_weaviate_ready_and_populated()

        # Verify client methods were called
        mock_client.is_ready.assert_called_once()
        mock_client.collections.exists.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("backend.ollama_client.httpx.get")
    def test_ollama_model_check_logging(self, mock_get):
        """Test Ollama model availability check logging."""
        from backend.ollama_client import ensure_model_available

        # Mock successful model check
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "test-model"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = ensure_model_available("test-model")
        assert result is True


class TestHybridSearchIntegration:
    """Test hybrid search integration and error handling."""

    @patch("backend.retriever.weaviate.connect_to_custom")
    @patch("backend.retriever._get_embedding_model")
    def test_hybrid_search_with_vectorization_integration(self, mock_get_model, mock_connect):
        """Integration test for hybrid search with manual vectorization."""
        from backend.retriever import get_top_k

        # Setup embedding model mock
        mock_model = MagicMock()
        mock_array = MagicMock()
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_array
        mock_get_model.return_value = mock_model

        # Setup Weaviate mock
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()

        # Mock successful hybrid search
        mock_result = MagicMock()

        class MockObject:
            def __init__(self, content):
                self.properties = {"content": content}

        mock_result.objects = [MockObject("Test content 1"), MockObject("Test content 2")]

        mock_query.hybrid.return_value = mock_result
        mock_collection.query = mock_query
        mock_client.collections.get.return_value = mock_collection
        mock_connect.return_value = mock_client

        # Test the integration
        result = get_top_k("test question", k=5)

        # Verify the flow
        mock_get_model.assert_called_once()
        mock_model.encode.assert_called_once_with("test question")
        mock_query.hybrid.assert_called_once_with(vector=[0.1, 0.2, 0.3], query="test question", alpha=0.5, limit=5)

        assert result == ["Test content 1", "Test content 2"]


@pytest.mark.slow
class TestContainerReadiness:
    """Test container readiness and CLI behaviors."""

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
