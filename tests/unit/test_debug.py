#!/usr/bin/env python3
"""Test script to demonstrate debug logging for Weaviate chunks."""

import logging
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.config import get_logger
from backend.console import console


def test_debug_logging():
    """Test debug logging with different log levels."""

    # Test with INFO level (default)
    console.print("=== Testing with INFO level (default) ===")
    logger = get_logger("test")
    logger.setLevel(logging.INFO)

    # Simulate what the debug logging would look like
    logger.info("This is an INFO message")
    logger.debug("This DEBUG message won't show with INFO level")

    console.print("\n" + "=" * 50 + "\n")

    # Test with DEBUG level
    console.print("=== Testing with DEBUG level ===")
    logger.setLevel(logging.DEBUG)

    logger.info("This is an INFO message")
    logger.debug("This DEBUG message WILL show with DEBUG level")

    # Simulate chunk debug output
    mock_chunks = [
        (
            "This is the first chunk of content that would be returned by Weaviate. "
            "It contains some sample text to demonstrate the debug logging functionality."
        ),
        (
            "This is the second chunk with different content. It shows how multiple "
            "chunks would be logged with their scores and distances."
        ),
        "Third chunk example with more content to show the full debug output format.",
    ]

    console.print("\n=== Simulated Weaviate chunk debug output ===")
    for i, content in enumerate(mock_chunks):
        logger.debug("Chunk %d:", i + 1)
        logger.debug("  Distance: 0.1234")
        logger.debug("  Score: 0.8765")
        logger.debug("  Content: %s", content[:100] + "..." if len(content) > 100 else content)
        logger.debug("  Content length: %d characters", len(content))
        console.print()


if __name__ == "__main__":
    test_debug_logging()
