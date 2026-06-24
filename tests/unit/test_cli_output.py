"""Tests for the CLI logging configuration."""

import logging
import os
from unittest.mock import patch

import pytest

from backend.config import set_log_level
from backend.qa_loop import _resolve_cli_log_level


@pytest.fixture(autouse=True)
def reset_logging_state():
    """Reset logging to a clean state for each test."""
    # Store original state
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    original_log_level_env = os.environ.get("LOG_LEVEL")

    # Reset to clean state. Detach handlers without logging.shutdown(): shutdown()
    # closes every handler process-wide, including pytest's log_file handler, which
    # is opened in mode "w" and never reopens once closed — silently dropping the
    # rest of the session from reports/test_session.log.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]

    # Reset the global configuration flag
    import backend.config

    backend.config._logging_configured = False

    yield

    # Restore original state (detach current handlers without closing them; see above).
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    for handler in original_handlers:
        logging.root.addHandler(handler)
    logging.root.level = original_level
    if original_log_level_env is not None:
        os.environ["LOG_LEVEL"] = original_log_level_env


def test_resolve_cli_log_level_with_different_flags():
    """Test that the CLI flag resolver returns the right level name for each combination."""
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
        assert _resolve_cli_log_level(log_level, verbose_count, quiet_count) == expected_level, (
            f"Expected {expected_level} for flags: log_level={log_level}, verbose={verbose_count}, quiet={quiet_count}"
        )


def test_resolve_cli_log_level_with_environment_variable():
    """Test that the resolver respects the LOG_LEVEL environment variable when no flags are set."""
    with patch.dict("os.environ", {"LOG_LEVEL": "WARNING"}):
        assert _resolve_cli_log_level(None, 0, 0) == "WARNING"


def test_set_log_level_function():
    """Test the set_log_level function directly."""
    # Test setting different levels
    test_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

    for level in test_levels:
        set_log_level(level)
        root_logger = logging.getLogger()
        expected_level = getattr(logging, level)
        assert root_logger.level == expected_level, f"Expected {level} level"
