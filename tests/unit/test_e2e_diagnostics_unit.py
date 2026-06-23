"""Unit tests for the e2e containerized-CLI failure diagnostics (P3 Step 7).

These exercise `tests.e2e.conftest._dump_container_diagnostics` in isolation with
`subprocess.run` mocked, so no Docker/network is touched — they run in the fast
unit tier despite covering an e2e helper.
"""

import logging
import subprocess

from tests.e2e.conftest import _DIAGNOSTIC_SERVICES, _dump_container_diagnostics


def test_dump_collects_logs_for_every_diagnostic_service(monkeypatch, caplog):
    """A failed CLI run dumps `docker compose logs` for each diagnostic service
    plus the CLI exit code and captured stdout/stderr."""
    requested_services: list[str] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        requested_services.append(cmd[-1])  # `docker compose ... logs --tail N <service>`
        return subprocess.CompletedProcess(cmd, 0, stdout="container log line", stderr="")

    monkeypatch.setattr("tests.e2e.conftest.subprocess.run", fake_run)

    failed = subprocess.CompletedProcess(["docker"], 1, stdout="boom-out", stderr="boom-err")
    with caplog.at_level(logging.ERROR, logger="tests.e2e.conftest"):
        _dump_container_diagnostics("docker/docker-compose.yml", failed)

    assert requested_services == list(_DIAGNOSTIC_SERVICES)
    text = caplog.text
    assert "exited 1" in text
    assert "boom-out" in text and "boom-err" in text


def test_dump_never_raises_when_docker_unavailable(monkeypatch):
    """Diagnostics run on the failure path and must not mask the original error
    if log collection itself fails."""

    def boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise OSError("docker not found")

    monkeypatch.setattr("tests.e2e.conftest.subprocess.run", boom)

    failed = subprocess.CompletedProcess(["docker"], 1, stdout="", stderr="")
    # Should swallow the OSError rather than propagate it.
    _dump_container_diagnostics("docker/docker-compose.yml", failed)
