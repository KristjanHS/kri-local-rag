#!/usr/bin/env python3
"""Test script to demonstrate Weaviate chunk debug logging."""

import os
import sys
import logging

# Set debug logging level
os.environ["LOG_LEVEL"] = "DEBUG"

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from config import get_logger
from retriever import get_top_k


def test_weaviate_debug():
    """Test Weaviate debug logging with actual queries."""

    logger = get_logger("weaviate_test")
    logger.setLevel(logging.DEBUG)

    print("=== Testing Weaviate Debug Logging ===")
    print("This will show detailed chunk information when debug=True")
    print("Make sure you have data in your Weaviate collection first!")
    print()

    # Test with a simple query
    test_questions = [
        "What is the main topic?",
        "Explain the key concepts",
        "What are the important points?",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"--- Test Query {i}: '{question}' ---")
        try:
            chunks = get_top_k(question, k=3)
            print(f"Found {len(chunks)} chunks")
            if chunks:
                print("Chunk previews:")
                for j, chunk in enumerate(chunks[:2], 1):  # Show first 2 chunks
                    preview = chunk[:100] + "..." if len(chunk) > 100 else chunk
                    print(f"  {j}. {preview}")
            print()
        except Exception as e:
            print(f"Error: {e}")
            print()


if __name__ == "__main__":
    test_weaviate_debug()
