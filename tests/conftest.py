"""Global pytest configuration for logging and per-test log capture."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterator

import pytest

REPORTS_DIR = Path("reports")
LOGS_DIR = REPORTS_DIR / "logs"


def pytest_sessionstart(session: pytest.Session) -> None:  # noqa: D401
    """Ensure report directories exist before any logging is configured."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _ensure_logs_dir() -> Iterator[None]:
    # Reduce noise from third-party libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("weaviate").setLevel(logging.INFO)
    yield


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Attach a per-test file handler to the root logger."""
    nodeid_sanitized = item.nodeid.replace(os.sep, "_").replace("::", "__")
    logfile = LOGS_DIR / f"{nodeid_sanitized}.log"
    logfile.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(logfile, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Store a reference so we can remove it later
    item._log_file_handler = handler  # type: ignore[attr-defined]

    root = logging.getLogger()
    root.addHandler(handler)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Detach the per-test file handler."""
    handler: logging.Handler | None = getattr(item, "_log_file_handler", None)  # type: ignore[attr-defined]
    if handler is not None:
        root = logging.getLogger()
        root.removeHandler(handler)
        handler.close()
        delattr(item, "_log_file_handler")  # type: ignore[attr-defined]


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:  # noqa: D401
    """On failure, emit path to the per-test logfile for quick discovery."""
    if report.when == "call" and report.failed:
        try:
            nodeid_sanitized = report.nodeid.replace(os.sep, "_").replace("::", "__")
            logfile = LOGS_DIR / f"{nodeid_sanitized}.log"
            logging.getLogger(__name__).warning("Per-test log: %s", logfile)
        except Exception:
            # best-effort; don't break test reporting
            pass


#!/usr/bin/env python3
"""Root-level pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root():
    """Provides the absolute path to the project root directory."""
    return Path(__file__).parent.parent


# Lightweight default for docker-based tests outside specialized suites.
# Suites can override this fixture in a closer-scope conftest (e.g. tests/e2e/conftest.py)
# to perform heavier readiness checks.
@pytest.fixture(scope="session")
def docker_services_ready():  # noqa: D401
    """No-op readiness fixture for generic docker-marked tests."""
    yield
