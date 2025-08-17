"""Tests for the CLI logging configuration."""

import logging
from unittest.mock import patch

import pytest

from backend.config import set_log_level
from backend.qa_loop import _setup_cli_logging


@pytest.fixture(autouse=True)
def reset_logging_state():
    """Reset logging to a clean state for each test."""
    # Store original state
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level

    # Reset to clean state
    logging.shutdown()
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Reset the global configuration flag
    import backend.config

    backend.config._logging_configured = False

    yield

    # Restore original state
    logging.shutdown()
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    for handler in original_handlers:
        logging.root.addHandler(handler)
    logging.root.level = original_level


def test_cli_logging_setup_with_different_flags():
    """Test that CLI logging setup correctly interprets different flag combinations."""
    import logging

    logger = logging.getLogger(__name__)

    test_cases = [
        # (log_level, verbose_count, quiet_count, expected_level)
        (None, 0, 0, "INFO"),  # Default
        (None, 1, 0, "INFO"),  # Single verbose
        (None, 2, 0, "DEBUG"),  # Double verbose
        (None, 0, 1, "WARNING"),  # Single quiet
        (None, 0, 2, "WARNING"),  # Double quiet
        ("ERROR", 0, 0, "ERROR"),  # Explicit level
        ("DEBUG", 2, 1, "DEBUG"),  # Explicit level takes precedence
    ]

    for log_level, verbose_count, quiet_count, expected_level in test_cases:
        # Set up logging
        _setup_cli_logging(log_level, verbose_count, quiet_count)

        # Verify the level was set correctly
        root_logger = logging.getLogger()
        expected_logging_level = getattr(logging, expected_level)

        logger.debug(
            "Testing flags: log_level=%s, verbose=%d, quiet=%d. Expected: %s, Got: %s",
            log_level,
            verbose_count,
            quiet_count,
            expected_level,
            logging.getLevelName(root_logger.level),
        )

        assert (
            root_logger.level == expected_logging_level
        ), f"Expected {expected_level} for flags: log_level={log_level}, verbose={verbose_count}, quiet={quiet_count}"


def test_cli_logging_setup_with_environment_variable():
    """Test that CLI logging setup respects the LOG_LEVEL environment variable."""
    with patch.dict("os.environ", {"LOG_LEVEL": "WARNING"}):
        _setup_cli_logging(None, 0, 0)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING


def test_set_log_level_function():
    """Test the set_log_level function directly."""
    # Test setting different levels
    test_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

    for level in test_levels:
        set_log_level(level)
        root_logger = logging.getLogger()
        expected_level = getattr(logging, level)
        assert root_logger.level == expected_level, f"Expected {level} level"
