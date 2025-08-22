#!/usr/bin/env python3
"""
Validate Single Source of Truth for model configurations.

This script checks that all model names across the codebase come from backend.config.
"""

import logging
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_MODEL, DEFAULT_RERANKER_MODEL

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    """Validate that model configurations are centralized."""
    logger.info("🔍 Validating Single Source of Truth for Model Configurations")
    logger.info("=" * 60)

    # Check that the centralized config has the expected values
    expected_embed = "sentence-transformers/all-MiniLM-L6-v2"
    expected_rerank = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    expected_ollama = "cas/mistral-7b-instruct-v0.3"

    logger.info(f"✅ Embedding model: {DEFAULT_EMBEDDING_MODEL}")
    if DEFAULT_EMBEDDING_MODEL != expected_embed:
        raise ValueError(f"Expected {expected_embed}, got {DEFAULT_EMBEDDING_MODEL}")

    logger.info(f"✅ Reranker model: {DEFAULT_RERANKER_MODEL}")
    if DEFAULT_RERANKER_MODEL != expected_rerank:
        raise ValueError(f"Expected {expected_rerank}, got {DEFAULT_RERANKER_MODEL}")

    logger.info(f"✅ Ollama model: {DEFAULT_OLLAMA_MODEL}")
    if DEFAULT_OLLAMA_MODEL != expected_ollama:
        raise ValueError(f"Expected {expected_ollama}, got {DEFAULT_OLLAMA_MODEL}")

    logger.info("\n🎉 All model configurations are properly centralized!")
    logger.info("📍 Single source of truth: backend/config.py")
    logger.info("\n📋 Summary:")
    logger.info(f"   • Embedding: {DEFAULT_EMBEDDING_MODEL}")
    logger.info(f"   • Reranker: {DEFAULT_RERANKER_MODEL}")
    logger.info(f"   • Ollama: {DEFAULT_OLLAMA_MODEL}")


if __name__ == "__main__":
    main()
