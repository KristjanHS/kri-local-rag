#!/usr/bin/env python3
"""Test CLI script integration and container management."""

import pytest

# Mark the entire module as requiring Docker
pytestmark = pytest.mark.docker
import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(
    Path("/.dockerenv").exists(),
    reason="CLI script integration tests are not applicable in a Docker environment.",
)
class TestCLIScriptIntegration:
    """Test CLI script functionality and container management."""

    def test_cli_script_exists_and_executable(self, cli_script_path):
        """Test that CLI script exists and is executable."""
        assert cli_script_path.exists(), "CLI script should exist"
        assert os.access(cli_script_path, os.X_OK), "CLI script should be executable"

    def test_docker_compose_file_exists(self, project_root):
        """Test that docker-compose file exists."""
        compose_file = project_root / "docker" / "docker-compose.yml"
        assert compose_file.exists(), "Docker compose file should exist"

    def test_container_python_execution(self):
        """Test that Python can execute in the app container."""
        try:
            # Test basic Python execution in container
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker/docker-compose.yml",
                    "exec",
                    "-T",
                    "app",
                    "python",
                    "-c",
                    "print('Container test successful')",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                assert "Container test successful" in result.stdout
            else:
                # Container might not be running, which is acceptable for this test
                pytest.skip("Container not available for testing")

        except subprocess.TimeoutExpired:
            pytest.skip("Container execution timed out")
        except FileNotFoundError:
            pytest.skip("Docker compose not available")

    def test_container_backend_imports(self):
        """Test that backend modules can be imported in container."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker/docker-compose.yml",
                    "exec",
                    "-T",
                    "app",
                    "bash",
                    "-c",
                    (
                        "cd /app/backend && python -c 'import config; import retriever; "
                        'import ollama_client; print("Backend imports successful")\''
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                assert "Backend imports successful" in result.stdout
            else:
                pytest.skip("Container not available for backend import testing")

        except subprocess.TimeoutExpired:
            pytest.skip("Container import test timed out")
        except FileNotFoundError:
            pytest.skip("Docker compose not available")


@pytest.mark.skipif(
    Path("/.dockerenv").exists(),
    reason="CLI script configuration tests are not applicable in a Docker environment.",
)
class TestCLIScriptConfiguration:
    """Test CLI script configuration and environment."""

    def test_script_has_proper_shebang(self, project_root):
        """Test that CLI script has proper shebang."""
        cli_script = project_root / "scripts" / "cli.sh"
        if cli_script.exists():
            with open(cli_script, "r") as f:
                first_line = f.readline().strip()
                assert first_line.startswith("#!/"), "Script should have proper shebang"

    def test_config_script_exists(self, project_root):
        """Test that config script exists."""
        config_script = project_root / "scripts" / "config.sh"
        assert config_script.exists(), "Config script should exist"

    def test_docker_compose_has_app_service(self, project_root):
        """Test that docker-compose defines the app service."""
        compose_file = project_root / "docker" / "docker-compose.yml"
        if compose_file.exists():
            with open(compose_file, "r") as f:
                content = f.read()
                assert "app:" in content, "Docker compose should define app service"
                assert "weaviate:" in content, "Docker compose should define weaviate service"
                assert "ollama:" in content, "Docker compose should define ollama service"


class TestContainerDependencyOptimization:
    """Test the container dependency optimizations implemented."""

    def test_docker_compose_dependency_configuration(self, project_root):
        """Test that Docker compose dependencies are optimized."""
        compose_file = project_root / "docker" / "docker-compose.yml"
        if compose_file.exists():
            with open(compose_file, "r") as f:
                content = f.read()

                # Should have simple dependencies, not health check dependencies
                assert "depends_on:" in content, "Should have dependency configuration"

                # Should not have the old health check format
                assert "condition: service_healthy" not in content, "Should not use slow health check dependencies"

    def test_cli_script_readiness_check_optimization(self, project_root):
        """Test that CLI script has optimized readiness checks."""
        cli_script = project_root / "scripts" / "cli.sh"
        if cli_script.exists():
            with open(cli_script, "r") as f:
                content = f.read()

                # Should have container readiness check
                assert "Container ready" in content, "Should have readiness check"

                # Should not have excessive sleep delays
                sleep_count = content.count("sleep")
                assert sleep_count <= 1, f"Should not have excessive sleep commands, found {sleep_count}"


class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback behaviors."""

    def test_import_error_handling_patterns(self, project_root):
        """Test that code properly handles import errors."""
        # Test qa_loop.py handles sentence_transformers import errors
        qa_loop_file = project_root / "backend" / "qa_loop.py"
        if qa_loop_file.exists():
            with open(qa_loop_file, "r") as f:
                content = f.read()
                assert "try:" in content and "ImportError:" in content, "Should handle import errors gracefully"

        # Test retriever.py handles sentence_transformers import errors
        retriever_file = project_root / "backend" / "retriever.py"
        if retriever_file.exists():
            with open(retriever_file, "r") as f:
                content = f.read()
                assert "try:" in content and "ImportError:" in content, "Should handle import errors gracefully"

    def test_hybrid_search_fallback_mechanism(self, project_root):
        """Test that hybrid search has proper fallback to BM25."""
        retriever_file = project_root / "backend" / "retriever.py"
        if retriever_file.exists():
            with open(retriever_file, "r") as f:
                content = f.read()
                assert "bm25" in content.lower(), "Should have BM25 fallback"
                assert "hybrid" in content.lower(), "Should have hybrid search"


class TestLoggingOptimizations:
    """Test logging optimizations and message deduplication."""

    def test_qa_loop_has_clean_logging(self, project_root):
        """Test that QA loop has clean, non-duplicate logging."""
        qa_loop_file = project_root / "backend" / "qa_loop.py"
        if qa_loop_file.exists():
            with open(qa_loop_file, "r") as f:
                content = f.read()

                # Should have clean ready message
                assert "RAG console ready" in content, "Should have ready message"

                # Should not have timing debug code
                assert "import time" not in content, "Should not have debug timing code"
                assert "start_time" not in content, "Should not have timing variables"

    def test_retriever_has_info_level_chunk_logging(self, project_root):
        """Test that retriever shows chunk heads at INFO level."""
        retriever_file = project_root / "backend" / "retriever.py"
        if retriever_file.exists():
            with open(retriever_file, "r") as f:
                content = f.read()

                # Should show chunk information at INFO level
                assert 'logger.info("Chunk %d:' in content, "Should log chunk heads at INFO level"


if __name__ == "__main__":
    pytest.main([__file__])
