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
    env_vars_to_restore = ["HF_HOME"]

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
