"""Unit tests for the centralized logging configuration."""

import logging
import logging.handlers
from unittest.mock import patch

import pytest
from rich.logging import RichHandler

from backend.config import set_log_level


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


def test_set_log_level_configures_handlers_correctly():
    """Verify that set_log_level properly configures the root logger and console handler."""
    # Test setting different log levels
    test_cases = [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
    ]

    for level_name, expected_level in test_cases:
        # Set the log level (this will also initialize logging if needed)
        set_log_level(level_name)

        # Verify root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == expected_level, f"Root logger level should be {expected_level} for {level_name}"

        # Verify console handler level
        rich_handlers = [h for h in root_logger.handlers if isinstance(h, RichHandler)]
        assert len(rich_handlers) == 1, "Should have exactly one RichHandler"
        assert rich_handlers[0].level == expected_level, (
            f"Console handler level should be {expected_level} for {level_name}"
        )


def test_set_log_level_handles_invalid_level():
    """Verify that set_log_level gracefully handles invalid log levels."""
    # Test with invalid level - patch the configured logger instead of logging.warning
    with patch("backend.config.get_logger") as mock_get_logger:
        mock_logger = mock_get_logger.return_value
        set_log_level("INVALID_LEVEL")

        # Should default to INFO
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

        # Should log a warning using the configured logger
        mock_logger.warning.assert_called_once_with("Invalid log level '%s'. Defaulting to INFO.", "INVALID_LEVEL")


def test_set_log_level_handles_edge_cases():
    """Verify that set_log_level handles edge cases gracefully."""
    # Test with None
    set_log_level(None)  # type: ignore
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO

    # Test with empty string
    set_log_level("")
    assert root_logger.level == logging.INFO

    # Test with whitespace-only string
    set_log_level("   ")
    assert root_logger.level == logging.INFO


def test_single_rich_handler_and_no_duplicate_stream_handlers():
    """Verify that importing key modules results in exactly one Rich console handler
    and one file handler, with no duplicate StreamHandlers on the root logger.
    """
    # Import the modules that might trigger logging setup
    # These imports are used for their side effects to trigger logging configuration

    # The imports above are sufficient - no need to access them as package attributes
    # since they're not exposed in the package namespace

    # Trigger logging setup by getting a logger
    from backend.config import get_logger

    get_logger("test")

    # Get the root logger
    root_logger = logging.getLogger()

    # Assertions - exclude pytest's LogCaptureHandler from the count
    rich_handlers = [h for h in root_logger.handlers if isinstance(h, RichHandler)]
    file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
    other_stream_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, RichHandler)
        and not isinstance(h, logging.handlers.TimedRotatingFileHandler)
        and not h.__class__.__name__.startswith("LogCapture")  # Exclude pytest handlers
    ]

    assert len(rich_handlers) == 1, f"Expected 1 RichHandler, but found {len(rich_handlers)}"
    assert len(file_handlers) == 1, f"Expected 1 TimedRotatingFileHandler, but found {len(file_handlers)}"
    assert not other_stream_handlers, f"Expected no other StreamHandlers, but found {len(other_stream_handlers)}"
