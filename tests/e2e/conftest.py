#!/usr/bin/env python3
"""Pytest configuration and lightweight fixtures for the E2E test suite.

Heavy docker service setup was moved to `tests/e2e/fixtures_ingestion.py` and
should be imported explicitly by tests that require real ingestion/services.
"""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def cli_script_path(project_root):
    """Provides the absolute path to the main CLI script."""
    return project_root / "scripts" / "cli.sh"


## No per-test socket toggling required; sockets are allowed by default in non-unit suites.
@pytest.fixture(autouse=True)
def _noop_e2e_network_fixture():
    yield
