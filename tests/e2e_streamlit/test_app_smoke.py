"""Smoke tests for the Streamlit app using Playwright.

These tests rely on env hooks to keep them fast and deterministic:
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


def test_root_health(streamlit_server):
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    resp = requests.get(base_url)
    assert resp.status_code == 200
    assert "streamlit" in resp.text.lower()


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


def test_server_is_fully_responsive(streamlit_server):
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    resp = requests.get(base_url)
    assert resp.status_code == 200
    assert "streamlit" in resp.text.lower()


def test_input_field_interaction(streamlit_server, page: Page):
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    page.goto(base_url)
    input_textbox = page.get_by_label("Ask a question:")
    expect(input_textbox).to_be_visible()
    test_input_text = "Test Query"
    input_textbox.fill(test_input_text)
    expect(input_textbox).to_have_value(test_input_text)


def test_submit_button_locator(streamlit_server, page: Page):
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    page.goto(base_url)
    submit_button = page.get_by_role("button", name="Get Answer")
    expect(submit_button).to_be_visible()


def test_answer_display_area_locator(streamlit_server, page: Page):
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    page.goto(base_url)
    # Only present after submission, so verify after click
    page.get_by_label("Ask a question:").fill("X")
    page.get_by_role("button", name="Get Answer").click()
    answer_area = page.locator("[data-testid='answer']")
    expect(answer_area).to_be_visible(timeout=15000)


def test_basic_interaction_flow(streamlit_server, page: Page):
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    page.goto(base_url)
    page.get_by_label("Ask a question:").fill("Hello, AI!")
    page.get_by_role("button", name="Get Answer").click()
    answer_root = page.locator("[data-testid='answer']")
    expect(answer_root).to_be_visible(timeout=15000)
    answer_content = answer_root.locator(".answer-content")
    expect(answer_content).not_to_be_empty()


def test_fake_mode_marker_present(streamlit_server, page: Page):
    base_url = os.environ.get("RAG_E2E_BASE_URL", "http://localhost:8501")
    page.goto(base_url)
    page.get_by_label("Ask a question:").fill("Hello")
    page.get_by_role("button", name="Get Answer").click()
    fake_mode_locator = page.locator("[data-testid='fake-mode']")
    expect(fake_mode_locator).to_have_count(1)
