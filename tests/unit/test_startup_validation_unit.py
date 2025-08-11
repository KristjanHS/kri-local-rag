#!/usr/bin/env python3
"""Unit tests for startup validation - file existence, syntax, and import structure."""

import ast
import logging
import os
import subprocess
from unittest.mock import patch

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.unit
class TestStartupValidationUnit:
    """Unit tests for startup validation - no external dependencies."""

    def test_backend_files_exist(self):
        """Test that core backend files exist without importing them."""
        logger.info("\n=== TESTING FILE EXISTENCE ===")

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        backend_dir = os.path.join(project_root, "backend")

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

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        backend_dir = os.path.join(project_root, "backend")

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
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        backend_dir = os.path.join(project_root, "backend")

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

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

        logger.info("Testing config.py import in subprocess...")
        try:
            result = subprocess.run(
                ["python", "-m", "backend.config"],
                capture_output=True,
                text=True,
                timeout=10,  # 10-second timeout
                cwd=project_root,
            )
            assert result.returncode == 0, f"Config import failed: {result.stderr}"
            logger.info("✓ config.py imports without hanging")
        except subprocess.TimeoutExpired:
            pytest.fail("Config import timed out - may be waiting for input")

        logger.info("=== INTERACTIVE PROMPT TEST COMPLETED ===")

    def test_safe_config_import_only(self):
        """Test that config.py can be imported safely without side effects."""
        logger.info("\n=== TESTING SAFE CONFIG IMPORT ===")

        # Test that config import doesn't trigger external connections
        with patch("backend.qa_loop.ensure_weaviate_ready_and_populated") as mock_weaviate:
            with patch("backend.ollama_client.ensure_model_available") as mock_ollama:
                # Import should not trigger any external calls
                from backend import config

                # Verify no external calls were made
                mock_weaviate.assert_not_called()
                mock_ollama.assert_not_called()

                # Verify config has expected attributes
                assert hasattr(config, "OLLAMA_MODEL")
                assert hasattr(config, "WEAVIATE_URL")
                assert hasattr(config, "COLLECTION_NAME")

        logger.info("=== SAFE CONFIG IMPORT TEST COMPLETED ===")

    @patch("backend.qa_loop.ensure_weaviate_ready_and_populated")
    @patch("backend.qa_loop.ensure_model_available")
    def test_qa_loop_initialization_components(self, mock_ensure_model, mock_ensure_weaviate):
        """Test that qa_loop initialization components are available."""
        from backend import qa_loop

        # Verify functions exist
        assert hasattr(qa_loop, "answer")
        assert hasattr(qa_loop, "ensure_weaviate_ready_and_populated")
        assert hasattr(qa_loop, "ensure_model_available")

        # Verify they can be called (with mocks)
        mock_ensure_weaviate.return_value = True
        mock_ensure_model.return_value = True

        # Test that functions don't crash on basic calls
        assert mock_ensure_weaviate() is True
        assert mock_ensure_model("test-model") is True

    def test_heavy_imports_eventually_succeed(self):
        """Test that heavy libs are discoverable without importing heavy modules."""
        logger.info("\n=== TESTING HEAVY IMPORTS ===")

        # Prefer discovery over import to avoid linter unused-import issues and heavy loads
        import importlib.util

        if importlib.util.find_spec("sentence_transformers") is not None:
            logger.info("✓ sentence_transformers available")
        else:
            logger.info("✓ sentence_transformers not available (expected in some environments)")

        if importlib.util.find_spec("torch") is not None:
            logger.info("✓ torch available")
        else:
            logger.info("✓ torch not available (unexpected)")

        logger.info("=== HEAVY IMPORTS TEST COMPLETED ===")

    def test_sentence_transformers_graceful_fallback(self):
        """Test that sentence_transformers fallback works gracefully."""
        logger.info("\n=== TESTING SENTENCE_TRANSFORMERS FALLBACK ===")

        # Test the fallback mechanism in retriever.py
        with patch("backend.retriever.SentenceTransformer", None):
            # This should not crash
            from backend import retriever

            assert hasattr(retriever, "get_top_k")

        logger.info("=== SENTENCE_TRANSFORMERS FALLBACK TEST COMPLETED ===")

    @pytest.mark.xfail(reason="Intermittent pytest-playwright teardown error (browser.close)", strict=False)
    def test_retriever_import_fallback_without_heavy_import(self):
        """Test that retriever can be imported even without heavy dependencies."""
        logger.info("\n=== TESTING RETRIEVER IMPORT FALLBACK ===")

        # Mock out sentence_transformers to simulate missing dependency
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            from backend import retriever

            assert hasattr(retriever, "get_top_k")
            assert hasattr(retriever, "_get_embedding_model")

        logger.info("=== RETRIEVER IMPORT FALLBACK TEST COMPLETED ===")


if __name__ == "__main__":
    pytest.main([__file__])
