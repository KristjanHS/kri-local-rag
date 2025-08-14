"""Validate that frontend runtime deps are present in the app container.

This is a lightweight import smoke test to catch missing packages such as
`streamlit` and `rich` that the frontend (directly or indirectly) relies on.
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = [pytest.mark.docker]


def test_frontend_requirements_inside_container() -> None:
    """Ensure key frontend/runtime deps import successfully in the app image."""
    # Run a one-off container for the app service and try to import modules.
    # Keep it minimal to be fast and reliable in CI.
    cmd = [
        "docker",
        "compose",
        "-f",
        "docker/docker-compose.yml",
        "run",
        "--rm",
        "app",
        "python",
        "-c",
        # streamlit: direct frontend dep; rich: indirect via backend.console used by app
        "import streamlit, rich; print('frontend_imports_ok')",
    ]
    out = subprocess.check_output(cmd, text=True)
    assert "frontend_imports_ok" in out
