#!/usr/bin/env python3
"""Test script to demonstrate Weaviate chunk debug logging."""

import logging
import os
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Set debug logging level
os.environ["LOG_LEVEL"] = "DEBUG"

from backend.config import get_logger
from backend.console import console
from backend.retriever import get_top_k


def test_weaviate_debug():
    """Test Weaviate debug logging with actual queries."""

    logger = get_logger("weaviate_test")
    logger.setLevel(logging.DEBUG)

    console.print("=== Testing Weaviate Debug Logging ===")
    console.print("This will show detailed chunk information when debug=True")
    console.print("Make sure you have data in your Weaviate collection first!")
    console.print()

    # Test with a simple query
    test_questions = [
        "What is the main topic?",
        "Explain the key concepts",
        "What are the important points?",
    ]

    for i, question in enumerate(test_questions, 1):
        console.print(f"--- Test Query {i}: '{question}' ---")
        try:
            chunks = get_top_k(question, k=3)
            console.print(f"Found {len(chunks)} chunks")
            if chunks:
                console.print("Chunk previews:")
                for j, chunk in enumerate(chunks[:2], 1):  # Show first 2 chunks
                    preview = chunk[:100] + "..." if len(chunk) > 100 else chunk
                    console.print(f"  {j}. {preview}")
            console.print()
        except Exception as e:
            console.print(f"Error: {e}")
            console.print()


if __name__ == "__main__":
    test_weaviate_debug()
