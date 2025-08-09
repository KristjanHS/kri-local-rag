import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.environment

# --- Constants for Environment Validation ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_PYTHON_PATH = PROJECT_ROOT / ".venv" / "bin" / "python"
BACKEND_CONFIG_PATH = PROJECT_ROOT / "backend" / "config.py"


@pytest.mark.skipif(Path("/.dockerenv").exists(), reason="Test not applicable in Docker container")
def test_python_executable_is_from_venv():
    """
    Verifies that the Python interpreter running the tests is the one
    from the project's virtual environment.
    """
    current_python_executable = Path(sys.executable).resolve()
    venv_path = PROJECT_ROOT / ".venv"

    if venv_path not in current_python_executable.parents:
        pytest.skip(
            "Pytest is running with a Python interpreter outside the virtual environment. "
            "This is acceptable in CI/CD but not recommended for local development."
        )

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
            "This likely means the project is not installed in editable mode. "
            "Run 'pip install -e .' from the project root. "
            f"Error: {e}"
        )
