import pytest

pytest_plugins = ["tests.e2e.fixtures_ingestion"]

pytestmark = [pytest.mark.slow, pytest.mark.external, pytest.mark.docker]


def test_e2e_answer_with_real_services_in_container(docker_services_ready, run_cli_in_container):  # noqa: ANN001
    """
    Asks a generic question through the containerized CLI; retrieval should find
    some context from the example_data ingested by docker_services_ready.
    """
    # Ask a generic question; retrieval should find some context from example_data
    result = run_cli_in_container(["--question", "Give me a brief summary of the indexed content.", "--k=2"])

    assert result.returncode == 0
    assert result.stdout.strip(), "Expected non-empty model output"
    assert "I found no relevant context" not in result.stdout, "Expected retrieval to provide context from Weaviate"
