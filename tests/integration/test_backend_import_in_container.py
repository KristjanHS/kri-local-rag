"""Minimal Docker packaging check.

Builds the app image and verifies that `backend` is importable inside the
container. This catches Dockerfile ordering errors.
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = [pytest.mark.docker, pytest.mark.slow]


def test_backend_import_inside_container() -> None:
    # Run a one-off container and check import (assumes image is built in CI harness)
    subprocess.check_call(
        [
            "docker",
            "compose",
            "-f",
            "docker/docker-compose.yml",
            "run",
            "--rm",
            "app",
            "python",
            "-c",
            "import backend,inspect; print(backend.__file__)",
        ]
    )
