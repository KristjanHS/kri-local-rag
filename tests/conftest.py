#!/usr/bin/env python3
"""Root-level pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent
