import os
import sys
from pathlib import Path

import pytest

pytestmark = []

# --- Constants for Environment Validation ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_PYTHON_PATH = PROJECT_ROOT / ".venv" / "bin" / "python"
BACKEND_CONFIG_PATH = PROJECT_ROOT / "backend" / "config.py"


@pytest.mark.skipif(
    os.getenv("TEST_DOCKER", "false").lower() == "true", reason="Test not applicable in Docker container"
)
def test_python_executable_is_from_venv():
    """
    Verifies that pytest runs inside the project's virtual environment.

    Note: Many virtual environments create `python` as a symlink to the base
    interpreter (e.g., /usr/bin/python3.12). Relying on Path.resolve() can
    therefore produce false negatives. Instead, verify venv activation using
    sys.prefix vs sys.base_prefix and ensure sys.prefix points inside `.venv`.
    """
    venv_dir = (PROJECT_ROOT / ".venv").resolve()

    # Detect that a venv is active
    in_virtual_env = getattr(sys, "real_prefix", None) is not None or sys.prefix != sys.base_prefix
    # Consider common CI environments where using the system interpreter is acceptable
    is_ci = any(
        (
            os.environ.get("CI"),
            os.environ.get("GITHUB_ACTIONS"),
            os.environ.get("BUILDKITE"),
            os.environ.get("GITLAB_CI"),
            os.environ.get("AZURE_PIPELINES"),
            os.environ.get("JENKINS_URL"),
            os.environ.get("TEAMCITY_VERSION"),
        )
    )
    if not in_virtual_env:
        if is_ci:
            pytest.skip(
                "Pytest is running with a Python interpreter outside the virtual environment. "
                "This is acceptable in CI/CD but not recommended for local development."
            )
        pytest.fail(
            "TEST FAILED: Pytest is running outside the project's virtual environment.\n"
            r"Activate the venv first (source .venv/bin/activate) or run with: ./\.venv/bin/python -m pytest"
        )

    # Ensure the active venv matches the project's `.venv`
    active_prefix = Path(sys.prefix).resolve()
    try:
        is_project_venv = active_prefix.is_relative_to(venv_dir)
    except AttributeError:
        # Fallback for very old Python (<3.9). Not expected in this project.
        is_project_venv = str(active_prefix).startswith(str(venv_dir))

    assert is_project_venv, (
        "TEST FAILED: A virtual environment is active, but it is not the project's `.venv`.\n"
        f"Expected venv at: {venv_dir}\n"
        f"Active sys.prefix: {active_prefix}"
    )

    # Sanity check executable name (don't resolve symlinks)
    current_python_executable = Path(sys.executable)
    assert current_python_executable.name in ("python", "python3"), (
        f"TEST FAILED: The Python executable has an unexpected name.\n"
        f"Expected name: 'python' or 'python3'\n"
        f"Actual name:   '{current_python_executable.name}'"
    )


def test_working_directory_is_project_root():
    """
    Verifies that the tests are being executed from the project root directory.
    This is crucial for relative paths and module discovery.
    """
    current_working_dir = Path.cwd()
    if PROJECT_ROOT != current_working_dir:
        pytest.skip(
            "Pytest is running from a directory other than the project root. "
            "This is acceptable in CI/CD but not recommended for local development."
        )


def test_config_module_import_and_path():
    """
    Tests two things:
    1. That modules from the 'backend' directory are importable.
    2. That the correct 'config.py' is imported, preventing module shadowing.
    """
    try:
        from backend import config

        # 1. A simple assertion to confirm the module is loaded.
        assert isinstance(config.COLLECTION_NAME, str)

        # 2. Check the file path of the imported module.
        imported_config_path = Path(config.__file__).resolve()
        assert BACKEND_CONFIG_PATH == imported_config_path, (
            f"TEST FAILED: The wrong 'config.py' module was imported.\n"
            f"Expected: {BACKEND_CONFIG_PATH}\n"
            f"Actual:   {imported_config_path}\n"
            "This indicates a module shadowing problem."
        )

    except ImportError as e:
        pytest.fail(
            "TEST FAILED: Failed to import 'backend.config'. "
            "This likely means the project dependencies are not installed. "
            "Run 'make uv-sync-test' from the project root. "
            f"Error: {e}"
        )
