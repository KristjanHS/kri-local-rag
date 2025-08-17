import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


def test_run_cli_in_container_help(run_cli_in_container):  # noqa: ANN001
    """
    Tests the --help command via the containerized CLI helper.
    This is a basic smoke test to ensure the helper and compose service are working.
    """
    result = run_cli_in_container(["--help"])
    assert result.returncode == 0
    assert "usage: qa_loop.py" in result.stdout
    assert "Interactive RAG console" in result.stdout
