import sys
from pathlib import Path

import pytest

# --- Debugging statements to inspect the test environment ---
print(f"DEBUG: sys.executable: {sys.executable}")
print(f"DEBUG: sys.path: {sys.path}")
# --- End of debugging statements ---


# --- Constants for Environment Validation ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON_PATH = PROJECT_ROOT / ".venv" / "bin" / "python"
BACKEND_CONFIG_PATH = PROJECT_ROOT / "backend" / "config.py"


def test_python_executable_is_from_venv():
    """
    Verifies that the Python interpreter running the tests is the one
    from the project's virtual environment.
    """
    # This test is flexible enough to handle both `python` and `python3` executables.
    current_python_executable = Path(sys.executable).resolve()
    venv_path = PROJECT_ROOT / ".venv"

    assert venv_path in current_python_executable.parents, (
        f"TEST FAILED: Pytest is running with a Python interpreter outside the virtual environment.\n"
        f"Expected interpreter from: {venv_path}\n"
        f"Actual interpreter:      {current_python_executable}\n"
        "Ensure you are using the command from the 'terminal_and_python.mdc' rule."
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
    assert PROJECT_ROOT == current_working_dir, (
        f"TEST FAILED: Pytest is running from the wrong directory.\n"
        f"Expected: {PROJECT_ROOT}\n"
        f"Actual:   {current_working_dir}\n"
        "Ensure the test command is run from the project root."
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
            "This likely means the PYTHONPATH is not set correctly by the test command. "
            f"Error: {e}"
        )
