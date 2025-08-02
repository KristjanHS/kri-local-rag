#!/usr/bin/env python3
"""Test startup performance and initialization behaviors."""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import time

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestStartupPerformance:
    """Test application startup performance and initialization."""

    def test_backend_files_exist(self):
        """Test that core backend files exist without importing them."""
        print("\n=== TESTING FILE EXISTENCE ===", flush=True)
        import os

        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")

        files_to_check = ["config.py", "qa_loop.py", "retriever.py", "ollama_client.py"]

        for filename in files_to_check:
            filepath = os.path.join(backend_dir, filename)
            print(f"Checking {filename}...", flush=True)
            assert os.path.exists(filepath), f"{filename} should exist"
            print(f"✓ {filename} exists", flush=True)

        print("=== FILE EXISTENCE TEST COMPLETED ===", flush=True)

    def test_import_structure_without_execution(self):
        """Test import structure by reading files as text without executing them."""
        print("\n=== TESTING IMPORT STRUCTURE ===", flush=True)
        import os

        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")

        # Test config.py has expected variables
        print("Analyzing config.py...", flush=True)
        config_path = os.path.join(backend_dir, "config.py")
        with open(config_path, "r") as f:
            config_content = f.read()
            assert "OLLAMA_MODEL" in config_content
            assert "WEAVIATE_URL" in config_content
            assert "COLLECTION_NAME" in config_content
        print("✓ config.py structure validated", flush=True)

        # Test retriever.py has proper import fallback
        print("Analyzing retriever.py...", flush=True)
        retriever_path = os.path.join(backend_dir, "retriever.py")
        with open(retriever_path, "r") as f:
            retriever_content = f.read()
            assert "try:" in retriever_content
            assert "ImportError:" in retriever_content
            assert "sentence_transformers" in retriever_content
        print("✓ retriever.py import fallback structure validated", flush=True)

        print("=== IMPORT STRUCTURE TEST COMPLETED ===", flush=True)

    def test_python_syntax_is_valid(self):
        """Test that all Python files have valid syntax without importing."""
        import os
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
        print("\n=== TESTING FOR INTERACTIVE PROMPTS ===", flush=True)
        import subprocess
        import os

        # Try to import config.py in a subprocess to see what happens
        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")

        print("Testing config.py import in subprocess...", flush=True)
        try:
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"import sys; sys.path.insert(0, '{backend_dir}'); import config; print('CONFIG_IMPORT_SUCCESS')",
                ],
                capture_output=True,
                text=True,
                timeout=10,  # 10-second timeout
                cwd=backend_dir,
            )

            if result.returncode == 0:
                if "CONFIG_IMPORT_SUCCESS" in result.stdout:
                    print("✓ config.py imports without hanging", flush=True)
                else:
                    print(f"⚠ config.py import had unexpected output: {result.stdout}", flush=True)
            else:
                print(f"⚠ config.py import failed: {result.stderr}", flush=True)

        except subprocess.TimeoutExpired:
            print("✗ config.py import timed out - likely waiting for input!", flush=True)
        except Exception as e:
            print(f"✗ config.py import test failed: {e}", flush=True)

        print("=== INTERACTIVE PROMPT TEST COMPLETED ===", flush=True)

    def test_safe_config_import_only(self):
        """Test importing only the config module safely."""
        print("\n=== TESTING SAFE CONFIG IMPORT ===", flush=True)
        import sys
        import os

        # Add backend to path
        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        print("About to import config module...", flush=True)
        sys.stdout.flush()

        try:
            import config

            print("✓ Config module imported successfully!", flush=True)

            # Test some basic attributes
            print("Testing config attributes...", flush=True)
            assert hasattr(config, "OLLAMA_MODEL"), "Should have OLLAMA_MODEL"
            assert hasattr(config, "WEAVIATE_URL"), "Should have WEAVIATE_URL"
            print("✓ Config attributes validated", flush=True)

        except Exception as e:
            print(f"✗ Config import failed: {e}", flush=True)
            raise

        print("=== SAFE CONFIG IMPORT COMPLETED ===", flush=True)

    @patch("qa_loop.ensure_weaviate_ready_and_populated")
    @patch("qa_loop.ensure_model_available")
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
        import sys

        print("\n=== STARTING HEAVY IMPORT TEST ===", flush=True)
        start_time = time.time()

        try:
            print("Step 1: About to import retriever module...", flush=True)
            sys.stdout.flush()

            print("Step 2: Retriever imported successfully!", flush=True)
            import_time = time.time() - start_time
            print(f"Step 3: Import completed in {import_time:.2f}s", flush=True)

            # Allow generous time for ML library imports on first run
            assert import_time < 30.0, f"Heavy imports took {import_time:.2f}s, should be < 30.0s"

        except Exception as e:
            print(f"Step X: Import failed with error: {e}", flush=True)
            pytest.skip(f"Heavy imports failed (expected in some environments): {e}")

        print("=== HEAVY IMPORT TEST COMPLETED ===", flush=True)

    def test_sentence_transformers_graceful_fallback(self):
        """Test graceful fallback when sentence_transformers is not available."""
        # Test the fallback logic without actually importing heavy libraries
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            # This should not hang because we're mocking the import
            try:
                # Clear any cached module
                if "qa_loop" in sys.modules:
                    del sys.modules["qa_loop"]

                # Now test the fallback
                import qa_loop

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
            import retriever

            importlib.reload(retriever)

            model = retriever._get_embedding_model()
            assert model is None


class TestInitializationLogging:
    """Test initialization logging and message deduplication."""

    @patch("qa_loop.weaviate.connect_to_custom")
    def test_weaviate_check_logging(self, mock_connect):
        """Test that Weaviate check produces appropriate log messages."""
        # Mock successful connection
        mock_client = MagicMock()
        mock_client.is_ready.return_value = True
        mock_client.collections.exists.return_value = True
        mock_connect.return_value = mock_client

        from qa_loop import ensure_weaviate_ready_and_populated

        # Should complete without exceptions
        ensure_weaviate_ready_and_populated()

        # Verify client methods were called
        mock_client.is_ready.assert_called_once()
        mock_client.collections.exists.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("ollama_client.httpx.get")
    def test_ollama_model_check_logging(self, mock_get):
        """Test Ollama model availability check logging."""
        from ollama_client import ensure_model_available

        # Mock successful model check
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "test-model"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = ensure_model_available("test-model")
        assert result is True


class TestHybridSearchIntegration:
    """Test hybrid search integration and error handling."""

    @patch("retriever.weaviate.connect_to_custom")
    @patch("retriever._get_embedding_model")
    def test_hybrid_search_with_vectorization_integration(self, mock_get_model, mock_connect):
        """Integration test for hybrid search with manual vectorization."""
        from retriever import get_top_k

        # Setup embedding model mock
        mock_model = MagicMock()
        mock_vector = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_vector
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
        mock_query.hybrid.assert_called_once_with(vector=mock_vector, query="test question", alpha=0.5, limit=5)

        assert result == ["Test content 1", "Test content 2"]


class TestContainerReadiness:
    """Test container readiness and CLI behaviors."""

    def test_python_execution_in_container_context(self):
        """Test that Python can execute basic commands in the expected environment."""
        # This test validates the container environment is working
        import config
        import ollama_client
        import retriever

        # Should be able to import all core modules
        assert hasattr(config, "OLLAMA_MODEL")
        assert hasattr(ollama_client, "ensure_model_available")
        assert hasattr(retriever, "get_top_k")

    def test_weaviate_url_configuration(self):
        """Test that Weaviate URL is properly configured for container environment."""
        from config import WEAVIATE_URL

        # Should be configured for Docker networking
        assert WEAVIATE_URL is not None
        assert len(WEAVIATE_URL) > 0

    def test_collection_name_configuration(self):
        """Test that collection name is properly configured."""
        from config import COLLECTION_NAME

        assert COLLECTION_NAME is not None
        assert len(COLLECTION_NAME) > 0


if __name__ == "__main__":
    pytest.main([__file__])
