#!/usr/bin/env python3
"""Comprehensive test script for logging functionality across the RAG system."""

import logging
import os
import tempfile

from backend.config import get_logger


def test_basic_logging():
    """Test basic logging functionality with different levels."""
    print("=== Testing Basic Logging ===")

    logger = get_logger("test_basic")

    # Test all log levels
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")

    print("Basic logging test completed\n")


def test_log_levels():
    """Test logging with different log levels."""
    print("=== Testing Log Levels ===")

    # Test with INFO level
    print("--- INFO Level ---")
    logger = get_logger("test_info")
    logger.setLevel(logging.INFO)
    logger.debug("This DEBUG message should NOT appear")
    logger.info("This INFO message should appear")
    logger.warning("This WARNING message should appear")

    # Test with DEBUG level
    print("\n--- DEBUG Level ---")
    logger.setLevel(logging.DEBUG)
    logger.debug("This DEBUG message should appear")
    logger.info("This INFO message should appear")

    print("Log levels test completed\n")


def test_log_formatting():
    """Test log message formatting and structure."""
    print("=== Testing Log Formatting ===")

    logger = get_logger("test_format")

    # Test different message types
    logger.info("Simple message")
    logger.info("Message with %s", "formatting")
    logger.info("Message with %d numbers", 42)
    logger.info("Message with %s and %d", "text", 123)

    # Test with structured data
    data = {"key": "value", "number": 42}
    logger.info("Structured data: %s", data)

    print("Log formatting test completed\n")


def test_logger_creation():
    """Test logger creation and configuration."""
    print("=== Testing Logger Creation ===")

    # Test creating multiple loggers
    loggers = []
    for i in range(3):
        logger = get_logger(f"test_logger_{i}")
        loggers.append(logger)
        logger.info(f"Logger {i} created successfully")

    # Test that they're all working
    for i, logger in enumerate(loggers):
        logger.info(f"Logger {i} is still working")

    print("Logger creation test completed\n")


def test_error_logging():
    """Test error logging and exception handling."""
    print("=== Testing Error Logging ===")

    logger = get_logger("test_error")

    try:
        # Simulate an error
        _ = 1 / 0
    except ZeroDivisionError as e:
        logger.error("Caught division by zero error: %s", e)
        logger.exception("Full exception traceback:")

    try:
        # Simulate another error
        undefined_variable
    except NameError as e:
        logger.error("Caught name error: %s", e)

    print("Error logging test completed\n")


def test_log_file_output():
    """Test logging to file (if file logging is configured)."""
    print("=== Testing Log File Output ===")

    # Create a temporary log file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as temp_file:
        temp_log_path = temp_file.name

    try:
        # Configure file handler for testing
        file_handler = logging.FileHandler(temp_log_path)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        logger = get_logger("test_file")
        logger.addHandler(file_handler)

        # Write some test messages
        logger.info("Test message to file")
        logger.debug("Debug message to file")
        logger.warning("Warning message to file")

        # Read and display the log file contents
        with open(temp_log_path, "r") as f:
            log_contents = f.read()
            print("Log file contents:")
            print(log_contents)

    finally:
        # Clean up
        if os.path.exists(temp_log_path):
            os.unlink(temp_log_path)

    print("Log file output test completed\n")


def test_weaviate_logging():
    """Test logging specifically for Weaviate operations."""
    print("=== Testing Weaviate Logging ===")

    logger = get_logger("test_weaviate")

    # Simulate Weaviate-related logging
    logger.info("Connecting to Weaviate...")
    logger.debug("Weaviate connection parameters: host=localhost, port=8080")

    # Simulate query logging
    logger.info("Executing Weaviate query")
    logger.debug("Query: nearText { concepts: ['test'] }")
    logger.debug("Query parameters: limit=10, offset=0")

    # Simulate response logging
    logger.info("Received response from Weaviate")
    logger.debug("Response contains 5 objects")

    print("Weaviate logging test completed\n")


def test_performance_logging():
    """Test logging for performance monitoring."""
    print("=== Testing Performance Logging ===")

    logger = get_logger("test_performance")

    import time

    # Simulate timing operations
    start_time = time.time()
    logger.info("Starting performance test")

    # Simulate some work
    time.sleep(0.1)

    elapsed = time.time() - start_time
    logger.info("Performance test completed in %.3f seconds", elapsed)

    # Simulate memory usage logging
    logger.debug("Memory usage: 128MB")
    logger.debug("CPU usage: 15%%")

    print("Performance logging test completed\n")


def run_all_tests():
    """Run all logging tests."""
    print("Starting comprehensive logging tests...\n")

    tests = [
        test_basic_logging,
        test_log_levels,
        test_log_formatting,
        test_logger_creation,
        test_error_logging,
        test_log_file_output,
        test_weaviate_logging,
        test_performance_logging,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"Test {test.__name__} failed: {e}")
            print()

    print("All logging tests completed!")


if __name__ == "__main__":
    # Set environment variable for debug logging if not already set
    if "LOG_LEVEL" not in os.environ:
        os.environ["LOG_LEVEL"] = "DEBUG"

    run_all_tests()
