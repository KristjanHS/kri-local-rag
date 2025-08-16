import subprocess
from pathlib import Path

from backend.config import EMBEDDING_MODEL, OLLAMA_MODEL


def test_relative_import_fails_when_run_as_script():
    """Verify that running the test file as a script fails due to relative imports."""
    # Create a temporary test file with a relative import
    test_file_content = "from . import some_nonexistent_module"
    test_file = Path(__file__).parent / "temp_test_import_script.py"
    with open(test_file, "w") as f:
        f.write(test_file_content)

    result = subprocess.run(
        ["python", str(test_file)],
        capture_output=True,
        text=True,
    )

    # Clean up the temporary file
    test_file.unlink()

    assert result.returncode != 0, "Script should fail when run directly"
    assert (
        "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr
    ), "Script should raise an ImportError or ModuleNotFoundError"


def test_absolute_imports_work():
    """Verify that absolute imports from the project root work correctly."""
    assert OLLAMA_MODEL, "OLLAMA_MODEL should be imported"
    assert EMBEDDING_MODEL, "EMBEDDING_MODEL should be imported"
