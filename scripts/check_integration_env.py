#!/usr/bin/env python3
"""
Integration Test Environment Checker

This script checks if your environment is properly set up for running integration tests.
Run this before running integration tests to identify any issues.
"""

import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from backend.config import get_service_url, is_running_in_docker
    from tests.integration.conftest import (
        get_available_services,
    )
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running from the project root directory")
    sys.exit(1)


def check_environment():
    """Check the current environment and service availability."""
    logger.info("🔍 Integration Test Environment Check")
    logger.info("=" * 50)

    # Check environment
    in_docker = is_running_in_docker()
    env_name = "Docker" if in_docker else "Local"
    logger.info(f"📍 Environment: {env_name}")

    # Check service availability
    logger.info("\n🔧 Service Availability:")
    services = get_available_services()

    weaviate_ok = services.get("weaviate", False)
    ollama_ok = services.get("ollama", False)

    weaviate_status = "✅ Available" if weaviate_ok else "❌ Not available"
    ollama_status = "✅ Available" if ollama_ok else "❌ Not available"

    logger.info(f"   Weaviate: {weaviate_status}")
    logger.info(f"   Ollama:   {ollama_status}")

    # Show connection details
    logger.info("\n🔗 Connection Details:")
    logger.info(f"   Weaviate URL:      {get_service_url('weaviate')}")
    logger.info(f"   Ollama URL:        {get_service_url('ollama')}")

    # Recommendations
    logger.info("\n💡 Recommendations:")

    if not weaviate_ok or not ollama_ok:
        logger.warning("   ❌ Some services are not available.")

        if not in_docker:
            logger.info("   📋 For local environment:")
            logger.info("      - Start Weaviate: docker run -d -p 8080:8080 semitechnologies/weaviate:latest")
            logger.info("      - Start Ollama: ollama serve")
            logger.info("      - Or use Docker environment: make test-up")
        else:
            logger.info("   📋 For Docker environment:")
            logger.info("      - Check if containers are running: make test-logs")
            logger.info("      - Restart environment: make test-down && make test-up")

    else:
        logger.info("   ✅ All services are available!")
        logger.info("   🚀 You can run integration tests now:")
        logger.info("      - All tests: .venv/bin/python -m pytest tests/integration/ -v")
        logger.info("      - Weaviate tests: .venv/bin/python -m pytest -m requires_weaviate -v")
        logger.info("      - Ollama tests: .venv/bin/python -m pytest -m requires_ollama -v")

    return weaviate_ok and ollama_ok


if __name__ == "__main__":
    success = check_environment()
    sys.exit(0 if success else 1)
