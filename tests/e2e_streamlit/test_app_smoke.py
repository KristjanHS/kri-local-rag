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
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


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


def test_interaction_basic(streamlit_server, page: Page):
    # Navigate to the app
    page.goto("http://localhost:8501", wait_until="domcontentloaded")

    # Streamlit renders a textarea for the question input
    page.get_by_role("textbox").first.fill("hello")

    # Click the submit button
    page.get_by_role("button", name="Get Answer").click()

    # Expect the Answer section and the fake answer injected via env
    expect(page.locator("text=Answer")).to_be_visible(timeout=10000)
    expect(page.locator("text=TEST_ANSWER")).to_be_visible(timeout=10000)
