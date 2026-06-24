import pytest

pytest_plugins = ["tests.e2e.fixtures_ingestion"]

pytestmark = [pytest.mark.slow, pytest.mark.docker]


def test_e2e_answer_with_real_services_in_container(docker_services_ready, run_cli_in_container):  # noqa: ANN001
    """
    Asks a generic question through the containerized CLI; retrieval should find
    some context from the example_data ingested by docker_services_ready.
    """
    # Ask a generic question; retrieval should find some context from example_data
    result = run_cli_in_container(["--question", "Give me a brief summary of the indexed content.", "--k=2"])

    # CLI succeeded and rendered an answer section. The CLI prints a
    # "Question:\n----\nAnswer: ..." block, so assert the banner is present
    # rather than at the very start of stdout.
    assert result.returncode == 0
    out = result.stdout.strip()
    assert out, "Expected non-empty CLI output"
    assert "Answer:" in out, "Expected CLI output to contain an 'Answer:' section"
    # Retrieval must actually find context from the ingested example data. The
    # empty-DB fallback means the collection was never populated (e.g. the
    # docker_services_ready ingestion fixture was shadowed) — fail loudly with a
    # retrieval-specific message instead of a cryptic banner mismatch.
    assert "I found no relevant context" not in out, (
        "Retrieval returned no context — the e2e collection was not populated by docker_services_ready"
    )
    # Ensure no crashes or tracebacks leaked to output
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    assert "Traceback" not in combined
