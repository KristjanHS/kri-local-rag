#!/usr/bin/env python3
"""Unit test for startup validation: importing config must not hang on input."""

import logging
import subprocess
import sys
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)


def test_config_import_does_not_hang():
    """`python -m backend.config` exits cleanly and doesn't block on interactive input.

    Guards against a regression where module-level config code waits for stdin
    (the one failure mode here a real bug could produce; file existence, syntax,
    and attribute presence are already enforced by every other test importing the
    package).
    """
    project_root = Path(__file__).resolve().parents[2]

    try:
        result = subprocess.run(
            [sys.executable, "-m", "backend.config"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Config import timed out - may be waiting for input")

    assert result.returncode == 0, f"Config import failed: {result.stderr}"


if __name__ == "__main__":
    pytest.main([__file__])
