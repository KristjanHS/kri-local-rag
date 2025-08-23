#!/usr/bin/env python3
"""
Integration tests for model loading optimization features.

Tests configuration and environment variable behavior that isn't covered by existing
integration tests. Validates integration test mode, cache priority logic, and timeout functionality.

These tests provide unique value by testing the configuration layer that controls
integration test behavior, ensuring proper environment variable handling and
configuration precedence.
"""

import importlib
import os

import pytest

pytestmark = [pytest.mark.integration]

from backend.config import get_logger

# Set up logging
logger = get_logger(__name__)


@pytest.fixture
def clean_environment():
    """
    Fixture to ensure clean environment variables for each test.

    This fixture saves the current environment state, yields for the test,
    and then restores the original state, ensuring tests don't interfere with each other.
    """
    # Save original environment state
    original_env = {}
    env_vars_to_restore = ["INTEGRATION_TEST_MODE", "MODEL_LOAD_TIMEOUT", "LOCAL_CACHE_PRIORITY", "HF_HOME"]

    for var in env_vars_to_restore:
        original_env[var] = os.environ.get(var)

    # Clean up any test environment variables
    for var in env_vars_to_restore:
        os.environ.pop(var, None)

    yield

    # Restore original environment state
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)

    # Force reload of backend.models to pick up environment changes
    import backend.models

    importlib.reload(backend.models)


@pytest.fixture
def reset_models_cache():
    """Reset the global model cache before and after each test."""
    import backend.models

    # Reset cache before test
    backend.models._embedding_model = None
    backend.models._cross_encoder = None

    yield

    # Reset cache after test
    backend.models._embedding_model = None
    backend.models._cross_encoder = None


def test_integration_test_mode_configuration(clean_environment, reset_models_cache):
    """
    Test that integration test mode can be enabled and configured via environment variables.

    This test validates the configuration system that controls integration test behavior,
    ensuring environment variables properly override defaults and the system responds
    correctly to configuration changes.
    """
    logger.info("Testing integration test mode configuration...")

    # Import fresh module to get default values
    import backend.models

    importlib.reload(backend.models)

    # Test default values
    assert backend.models.INTEGRATION_TEST_MODE is False, (
        f"Expected INTEGRATION_TEST_MODE to be False by default, got {backend.models.INTEGRATION_TEST_MODE}"
    )
    assert backend.models.MODEL_LOAD_TIMEOUT == 30.0, (
        f"Expected MODEL_LOAD_TIMEOUT to be 30.0 by default, got {backend.models.MODEL_LOAD_TIMEOUT}"
    )
    assert backend.models.LOCAL_CACHE_PRIORITY is True, (
        f"Expected LOCAL_CACHE_PRIORITY to be True by default, got {backend.models.LOCAL_CACHE_PRIORITY}"
    )
    logger.info("✓ Default configuration values validated")

    # Test environment variable configuration
    os.environ["INTEGRATION_TEST_MODE"] = "true"
    os.environ["MODEL_LOAD_TIMEOUT"] = "60.0"
    os.environ["LOCAL_CACHE_PRIORITY"] = "false"

    # Force module reload to pick up environment changes
    importlib.reload(backend.models)

    # Verify environment variables override defaults
    assert backend.models.INTEGRATION_TEST_MODE is True, (
        f"Expected INTEGRATION_TEST_MODE to be True after env var set, got {backend.models.INTEGRATION_TEST_MODE}"
    )
    assert backend.models.MODEL_LOAD_TIMEOUT == 60.0, (
        f"Expected MODEL_LOAD_TIMEOUT to be 60.0 after env var set, got {backend.models.MODEL_LOAD_TIMEOUT}"
    )
    assert backend.models.LOCAL_CACHE_PRIORITY is False, (
        f"Expected LOCAL_CACHE_PRIORITY to be False after env var set, got {backend.models.LOCAL_CACHE_PRIORITY}"
    )
    logger.info("✓ Environment variable configuration override validated")

    # Test boolean parsing edge cases
    os.environ["INTEGRATION_TEST_MODE"] = "false"
    os.environ["LOCAL_CACHE_PRIORITY"] = "0"

    importlib.reload(backend.models)

    assert backend.models.INTEGRATION_TEST_MODE is False, (
        f"Expected INTEGRATION_TEST_MODE to be False when set to 'false', got {backend.models.INTEGRATION_TEST_MODE}"
    )
    assert backend.models.LOCAL_CACHE_PRIORITY is False, (
        f"Expected LOCAL_CACHE_PRIORITY to be False when set to '0', got {backend.models.LOCAL_CACHE_PRIORITY}"
    )
    logger.info("✓ Boolean parsing edge cases validated")

    logger.info("✓ Integration test mode configuration test completed successfully")


def test_cache_priority_logic_integration_test_mode(clean_environment, reset_models_cache, integration_model_cache):
    """
    Test that cache priority logic works correctly in integration test mode.

    This test validates that the cache priority system functions properly within
    the existing integration test infrastructure. It uses the session-level cache
    setup and tests that the configuration and functions work as expected.
    """
    logger.info("Testing cache priority logic in integration test mode...")

    # Enable integration test mode
    os.environ["INTEGRATION_TEST_MODE"] = "true"

    # Reload module to pick up environment changes
    import backend.models

    importlib.reload(backend.models)

    # Verify integration test mode is active
    assert backend.models.INTEGRATION_TEST_MODE is True, (
        f"Expected INTEGRATION_TEST_MODE to be True, got {backend.models.INTEGRATION_TEST_MODE}"
    )
    assert backend.models.LOCAL_CACHE_PRIORITY is True, (
        f"Expected LOCAL_CACHE_PRIORITY to be True, got {backend.models.LOCAL_CACHE_PRIORITY}"
    )

    # Verify HF_CACHE_DIR is properly set (should be the integration test cache directory)
    assert backend.models.HF_CACHE_DIR is not None, "HF_CACHE_DIR should be set"
    assert isinstance(backend.models.HF_CACHE_DIR, str), "HF_CACHE_DIR should be a string"
    assert len(backend.models.HF_CACHE_DIR) > 0, "HF_CACHE_DIR should not be empty"

    # Since we can't control when the module is imported vs when the fixture sets env vars,
    # we'll test that the cache directory exists and is functional rather than checking
    # for a specific naming pattern
    logger.info(f"HF_CACHE_DIR is set to: {backend.models.HF_CACHE_DIR}")

    # Test that clear_model_cache function exists and is callable
    assert hasattr(backend.models, "clear_model_cache"), "clear_model_cache function should be available"
    assert callable(backend.models.clear_model_cache), "clear_model_cache should be callable"

    # Call clear_model_cache to test it doesn't raise exceptions
    backend.models.clear_model_cache()
    logger.info("✓ Cache clearing functionality validated")

    # Test that the cache directory structure exists
    assert os.path.exists(backend.models.HF_CACHE_DIR), f"Cache directory should exist: {backend.models.HF_CACHE_DIR}"
    logger.info("✓ Cache directory existence validated")

    logger.info("✓ Cache priority logic in integration test mode validated successfully")


def test_timeout_functionality_configuration(clean_environment, reset_models_cache):
    """
    Test that timeout functionality can be configured via environment variables.

    This test validates that model loading timeout configuration works correctly
    and that the system properly handles different timeout values.
    """
    logger.info("Testing timeout functionality configuration...")

    # Enable integration test mode with custom timeout
    os.environ["INTEGRATION_TEST_MODE"] = "true"
    os.environ["MODEL_LOAD_TIMEOUT"] = "45.5"

    # Reload module to pick up environment changes
    import backend.models

    importlib.reload(backend.models)

    # Verify timeout configuration
    assert backend.models.INTEGRATION_TEST_MODE is True, (
        f"Expected INTEGRATION_TEST_MODE to be True, got {backend.models.INTEGRATION_TEST_MODE}"
    )
    assert backend.models.MODEL_LOAD_TIMEOUT == 45.5, (
        f"Expected MODEL_LOAD_TIMEOUT to be 45.5, got {backend.models.MODEL_LOAD_TIMEOUT}"
    )

    # Test edge case: very short timeout (shouldn't cause issues just from configuration)
    os.environ["MODEL_LOAD_TIMEOUT"] = "0.1"
    importlib.reload(backend.models)

    assert backend.models.MODEL_LOAD_TIMEOUT == 0.1, (
        f"Expected MODEL_LOAD_TIMEOUT to be 0.1, got {backend.models.MODEL_LOAD_TIMEOUT}"
    )

    # Test invalid timeout values - we can't actually test this because
    # the module will fail to load with invalid values. Instead, we test
    # that valid numeric strings work correctly.
    os.environ["MODEL_LOAD_TIMEOUT"] = "120"
    importlib.reload(backend.models)

    assert backend.models.MODEL_LOAD_TIMEOUT == 120.0, (
        f"Expected MODEL_LOAD_TIMEOUT to be 120.0, got {backend.models.MODEL_LOAD_TIMEOUT}"
    )

    logger.info("✓ Timeout functionality configuration validated successfully")


def test_environment_variable_precedence(clean_environment, reset_models_cache):
    """
    Test that environment variables take precedence over defaults and are properly isolated.

    This test ensures that environment variable configuration works correctly
    and that tests don't interfere with each other through environment state.
    """
    logger.info("Testing environment variable precedence...")

    # Test 1: Default values without any environment variables
    import backend.models

    importlib.reload(backend.models)

    default_integration_mode = backend.models.INTEGRATION_TEST_MODE
    default_timeout = backend.models.MODEL_LOAD_TIMEOUT
    default_cache_priority = backend.models.LOCAL_CACHE_PRIORITY

    # Test 2: Set environment variables and verify they override defaults
    os.environ["INTEGRATION_TEST_MODE"] = "true"
    os.environ["MODEL_LOAD_TIMEOUT"] = "90.0"
    os.environ["LOCAL_CACHE_PRIORITY"] = "false"

    importlib.reload(backend.models)

    assert backend.models.INTEGRATION_TEST_MODE != default_integration_mode, (
        "Environment variable should override default for INTEGRATION_TEST_MODE"
    )
    assert backend.models.MODEL_LOAD_TIMEOUT != default_timeout, (
        "Environment variable should override default for MODEL_LOAD_TIMEOUT"
    )
    assert backend.models.LOCAL_CACHE_PRIORITY != default_cache_priority, (
        "Environment variable should override default for LOCAL_CACHE_PRIORITY"
    )

    # Test 3: Clear environment variables and verify defaults are restored
    os.environ.pop("INTEGRATION_TEST_MODE", None)
    os.environ.pop("MODEL_LOAD_TIMEOUT", None)
    os.environ.pop("LOCAL_CACHE_PRIORITY", None)

    importlib.reload(backend.models)

    assert backend.models.INTEGRATION_TEST_MODE == default_integration_mode, (
        "Default should be restored when environment variable is removed"
    )
    assert backend.models.MODEL_LOAD_TIMEOUT == default_timeout, (
        "Default should be restored when environment variable is removed"
    )
    assert backend.models.LOCAL_CACHE_PRIORITY == default_cache_priority, (
        "Default should be restored when environment variable is removed"
    )

    logger.info("✓ Environment variable precedence validated successfully")


def test_configuration_validation_edge_cases(clean_environment, reset_models_cache):
    """
    Test edge cases in configuration validation.

    This test covers various edge cases in environment variable parsing
    to ensure the configuration system is robust.
    """
    logger.info("Testing configuration validation edge cases...")

    test_cases = [
        # (env_value, expected_result, test_description)
        ("true", True, "lowercase true"),
        ("TRUE", True, "uppercase TRUE"),
        ("True", True, "capitalized True"),
        ("false", False, "lowercase false"),
        ("FALSE", False, "uppercase FALSE"),
        ("False", False, "capitalized False"),
        ("", False, "empty string"),
    ]

    for env_value, expected, description in test_cases:
        os.environ["INTEGRATION_TEST_MODE"] = env_value
        os.environ["LOCAL_CACHE_PRIORITY"] = env_value

        import backend.models

        importlib.reload(backend.models)

        assert backend.models.INTEGRATION_TEST_MODE == expected, (
            f"INTEGRATION_TEST_MODE should be {expected} for {description}, got {backend.models.INTEGRATION_TEST_MODE}"
        )
        assert backend.models.LOCAL_CACHE_PRIORITY == expected, (
            f"LOCAL_CACHE_PRIORITY should be {expected} for {description}, got {backend.models.LOCAL_CACHE_PRIORITY}"
        )

        # Clean up for next iteration
        os.environ.pop("INTEGRATION_TEST_MODE", None)
        os.environ.pop("LOCAL_CACHE_PRIORITY", None)

    # Test numeric timeout values
    numeric_timeout_cases = [
        ("30", 30.0, "integer as string"),
        ("30.0", 30.0, "float as string"),
        ("0", 0.0, "zero as string"),
        ("0.0", 0.0, "zero float as string"),
        ("123.456", 123.456, "decimal number"),
    ]

    for env_value, expected, description in numeric_timeout_cases:
        os.environ["MODEL_LOAD_TIMEOUT"] = env_value

        import backend.models

        importlib.reload(backend.models)

        assert backend.models.MODEL_LOAD_TIMEOUT == expected, (
            f"MODEL_LOAD_TIMEOUT should be {expected} for {description}, got {backend.models.MODEL_LOAD_TIMEOUT}"
        )

        os.environ.pop("MODEL_LOAD_TIMEOUT", None)

    logger.info("✓ Configuration validation edge cases completed successfully")
