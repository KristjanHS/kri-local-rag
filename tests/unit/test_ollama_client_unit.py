#!/usr/bin/env python3

from typing import cast

import httpx

from backend import ollama_client as oc
from backend.config import OLLAMA_MODEL


class DummyResp:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {"models": [{"name": f"{OLLAMA_MODEL}:latest"}]}

    def raise_for_status(self):
        if not (200 <= self.status_code < 400):
            req = httpx.Request("GET", "http://test.local/tags")
            resp = httpx.Response(500, request=req)
            raise httpx.HTTPStatusError("bad", request=req, response=resp)

    def json(self):
        return self._json_data


def test_check_model_exists_exact_and_prefix():
    models = [{"name": "a/b:latest"}, {"name": "x/y"}]
    assert oc._check_model_exists("a/b:latest", models) is True
    assert oc._check_model_exists("a/b", models) is True
    assert oc._check_model_exists("z", models) is False


def test_detect_model_uses_tags_endpoint(monkeypatch):
    def fake_get(url, timeout):  # noqa: ARG001
        assert url.endswith("/api/tags")
        return DummyResp(200)

    monkeypatch.setattr(httpx, "get", fake_get)
    model = oc._detect_ollama_model()
    assert isinstance(model, str) and model


def test_generate_response_handles_empty_and_exception(monkeypatch, caplog):
    # Force base url
    monkeypatch.setenv("DOCKER_ENV", "0")

    # Simulate streaming JSON lines then done
    class StreamResp:
        def __init__(self):
            self.status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401, ARG001
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield 'data: {"response": "hello", "done": true}\n'

    def fake_stream(method, url, json, timeout):  # noqa: ARG001
        assert method == "POST" and url.endswith("/api/generate")
        return StreamResp()

    monkeypatch.setattr(httpx, "stream", fake_stream)

    text, _ = oc.generate_response("hi", on_token=None, on_debug=None, stop_event=None, context_tokens=64)
    assert "hello" in text

    # Now simulate exception path
    def fake_stream_err(method, url, json, timeout):  # noqa: ARG001
        raise httpx.ConnectError("boom", request=None)

    import logging as _logging

    caplog.set_level(_logging.ERROR, logger=oc.__name__)

    monkeypatch.setattr(httpx, "stream", fake_stream_err)
    text, _ = oc.generate_response("hi", on_token=None, on_debug=None, stop_event=None, context_tokens=64)
    assert "Error generating response" in text
    msgs = [rec.getMessage() for rec in caplog.records]
    assert any("Exception in generate_response" in m for m in msgs)


def test_ensure_model_available_issues_single_pull_with_short_timeout(monkeypatch):
    seen: dict[str, object] = {"method": None, "url": None, "json": None, "timeout": None}

    class FakeResp:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):  # noqa: A002, ARG001
        seen["method"] = "POST"
        seen["url"] = url
        seen["json"] = json
        seen["timeout"] = timeout
        return FakeResp()

    monkeypatch.setenv("DOCKER_ENV", "0")
    monkeypatch.setattr(httpx, "post", fake_post)

    ok = oc.ensure_model_available("some/model:tag")
    assert ok is True

    seen_url = cast(str, seen["url"])
    assert seen["method"] == "POST"
    assert seen_url.endswith("/api/pull")
    assert seen["json"] == {"name": "some/model:tag"}
    assert isinstance(seen["timeout"], int) and seen["timeout"] <= 10


def test_download_model_with_progress_uses_timeout_in_stream(monkeypatch):
    seen: dict[str, object] = {"timeout": None, "url": None, "method": None}

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401, ARG001
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield b'{\n"status": "verifying"}\n'
            yield b'{\n"status": "complete"}\n'

    def fake_stream(method, url, json, timeout):  # noqa: ARG001
        seen["method"] = method
        seen["url"] = url
        seen["timeout"] = timeout
        return FakeStream()

    monkeypatch.setattr(httpx, "stream", fake_stream)

    ok = oc._download_model_with_progress("some/model:tag", "http://localhost:11434")
    assert ok is True
    assert seen["method"] == "POST"
    seen_url = cast(str, seen["url"])
    assert seen_url.endswith("/api/pull")
    assert seen["timeout"] == 300
