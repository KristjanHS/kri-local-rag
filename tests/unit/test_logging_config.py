"""Unit tests for the centralized logging configuration."""

import logging
from unittest.mock import patch

import pytest
from rich.logging import RichHandler

from backend.config import get_logger, set_log_level


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
    """Verify that set_log_level properly configures the root logger and console/stream handler."""
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

        # Verify console-like handler level (RichHandler in TTY, StreamHandler otherwise)
        console_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, (RichHandler, logging.StreamHandler))
            and not isinstance(h, logging.FileHandler)
            and not h.__class__.__name__.startswith("LogCapture")
        ]
        assert len(console_handlers) == 1, "Should have exactly one console handler"
        assert console_handlers[0].level == expected_level, (
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


def test_single_console_handler_and_no_duplicate_stream_handlers():
    """Verify that importing key modules results in exactly one console handler
    and no duplicate extra StreamHandlers on the root logger. No default file handler.
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
    console_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, (RichHandler, logging.StreamHandler))
        and not isinstance(h, logging.FileHandler)
        and not h.__class__.__name__.startswith("LogCapture")
    ]
    file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]

    assert len(console_handlers) == 1, f"Expected 1 console handler, but found {len(console_handlers)}"
    # By default we should not attach a file handler unless APP_LOG_DIR is set
    assert len(file_handlers) == 0, f"Expected no FileHandler by default, but found {len(file_handlers)}"


def test_file_logging_uses_timed_rotation_when_env_set(monkeypatch, tmp_path):
    """Verify that setting APP_LOG_DIR creates a TimedRotatingFileHandler with retention."""
    monkeypatch.setenv("APP_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("APP_LOG_BACKUP_COUNT", "5")

    # Trigger logging setup
    get_logger("test_file_rotation")

    root_logger = logging.getLogger()
    handlers = root_logger.handlers
    # Expect one TimedRotatingFileHandler present
    rotating_handlers = [h for h in handlers if h.__class__.__name__ == "TimedRotatingFileHandler"]
    assert len(rotating_handlers) == 1, "TimedRotatingFileHandler should be configured when APP_LOG_DIR is set"

    # Verify backupCount is set correctly from environment variable
    from logging.handlers import TimedRotatingFileHandler

    rotating_handler = rotating_handlers[0]
    assert isinstance(rotating_handler, TimedRotatingFileHandler)
    assert rotating_handler.backupCount == 5, (
        "backupCount should be set to 5 from APP_LOG_BACKUP_COUNT environment variable"
    )

    # Write a message to ensure file exists
    root_logger.info("rotation smoke")
    assert (tmp_path / "rag_system.log").exists(), "rag_system.log should be created"
