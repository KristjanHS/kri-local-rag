#!/usr/bin/env python3
"""Test script to demonstrate debug logging for Weaviate chunks."""

import os
import sys
import logging

# Add the backend directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from config import get_logger
from retriever import get_top_k


def test_debug_logging():
    """Test debug logging with different log levels."""

    # Test with INFO level (default)
    print("=== Testing with INFO level (default) ===")
    logger = get_logger("test")
    logger.setLevel(logging.INFO)

    try:
        chunks = get_top_k("test question", k=3, debug=True)
        print(f"Found {len(chunks)} chunks")
    except Exception as e:
        print(f"Error with INFO level: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test with DEBUG level
    print("=== Testing with DEBUG level ===")
    logger.setLevel(logging.DEBUG)

    try:
        chunks = get_top_k("test question", k=3, debug=True)
        print(f"Found {len(chunks)} chunks")
    except Exception as e:
        print(f"Error with DEBUG level: {e}")


if __name__ == "__main__":
    test_debug_logging()
