"""Smoke test for the Streamlit app using Playwright.

This test relies on env hooks to keep it fast and deterministic:
- RAG_SKIP_STARTUP_CHECKS=1   → skip slow readiness checks in backend
- RAG_FAKE_ANSWER=...         → bypass network/model calls in backend.answer
- RAG_VERBOSE_TEST=1          → optional log banners
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
from contextlib import closing

import pytest
import requests
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.slow]


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


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def streamlit_server():
    port = _find_free_port()
    env = {
        **os.environ,
        "RAG_SKIP_STARTUP_CHECKS": "1",
        "RAG_FAKE_ANSWER": "TEST_ANSWER",
        "RAG_VERBOSE_TEST": "1",
        # Streamlit: keep output simple and headless
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    }
    logging.getLogger(__name__).info(
        "Launching Streamlit with env: RAG_SKIP_STARTUP_CHECKS=%s, RAG_FAKE_ANSWER=%s",
        env.get("RAG_SKIP_STARTUP_CHECKS"),
        bool(env.get("RAG_FAKE_ANSWER")),
    )
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/rag_app.py",
        "--server.headless",
        "true",
        "--server.port",
        str(port),
        "--server.fileWatcherType",
        "none",
    ]
    # Write Streamlit server output to a logfile for diagnostics without risking PIPE blocking
    logs_dir = os.path.join("reports", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    server_log_path = os.path.join(logs_dir, f"streamlit_server_{port}.log")
    server_log = open(server_log_path, "a", encoding="utf-8")
    logging.getLogger(__name__).info("Streamlit server log: %s", server_log_path)
    proc = subprocess.Popen(cmd, stdout=server_log, stderr=subprocess.STDOUT, env=env)
    try:
        base_url = f"http://localhost:{port}"
        os.environ["RAG_E2E_BASE_URL"] = base_url
        logging.getLogger(__name__).info("Streamlit base URL: %s", base_url)
        _wait_http_ready(base_url)
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        try:
            server_log.close()
        except Exception:
            pass


def test_interaction_basic(streamlit_server, page: Page):
    # Navigate to the app
    page.set_default_timeout(15000)
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
    except Exception:
        time.sleep(0.5)
        page.goto(base_url, wait_until="domcontentloaded")

    # Streamlit renders a textarea for the question input
    page.get_by_label("Ask a question:").fill("hello")

    # Click the submit button
    page.get_by_role("button", name="Get Answer").click()

    # Optional small diagnostic wait to help confirm timing races under CI load
    diag_wait_ms = os.getenv("RAG_E2E_DIAG_WAIT")
    if diag_wait_ms:
        try:
            page.wait_for_timeout(int(diag_wait_ms))
        except Exception:
            # Fallback to a small fixed delay if parsing fails
            page.wait_for_timeout(300)

    # Expect the Answer section (stable locator) and the fake answer injected via env
    answer_root = page.locator("[data-testid='answer']")
    expect(answer_root).to_be_visible(timeout=20000)
    expect(answer_root.locator(".answer-content")).to_contain_text("TEST_ANSWER", timeout=20000)
