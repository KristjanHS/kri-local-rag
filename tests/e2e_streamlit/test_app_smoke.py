"""Smoke tests for the Streamlit app using Playwright.

These tests rely on env hooks to keep them fast and deterministic:
- RAG_SKIP_STARTUP_CHECKS=1   → skip slow readiness checks in backend
- RAG_FAKE_ANSWER=...         → bypass network/model calls in backend.answer
- RAG_VERBOSE_TEST=1          → optional log banners
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from contextlib import closing

import pytest
import requests


pytestmark = pytest.mark.e2e


def _wait_http_ready(url: str, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with closing(requests.get(url, timeout=2.0)) as resp:
                if resp.status_code == 200:
                    return
        except Exception as e:  # noqa: BLE001 - best-effort readiness
            last_err = e
        time.sleep(0.5)
    if last_err:
        raise AssertionError(f"App did not become ready at {url}: {last_err}")
    raise AssertionError(f"App did not become ready at {url}: unknown error")


@pytest.fixture(scope="module")
def streamlit_server():
    env = {
        **os.environ,
        "RAG_SKIP_STARTUP_CHECKS": "1",
        "RAG_FAKE_ANSWER": "TEST_ANSWER",
        "RAG_VERBOSE_TEST": "1",
        # Streamlit: keep output simple and headless
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    }
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/rag_app.py",
        "--server.headless",
        "true",
        "--server.port",
        "8501",
        "--server.fileWatcherType",
        "none",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    try:
        _wait_http_ready("http://localhost:8501")
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def test_root_health(streamlit_server):
    resp = requests.get("http://localhost:8501")
    assert resp.status_code == 200
    assert "streamlit" in resp.text.lower()


@pytest.mark.skip(reason="Minimal smoke does not cover UI automation without browser; add playwright-based tests next.")
def test_interaction_placeholder(streamlit_server):
    # Placeholder for future Playwright interaction test
    assert True
