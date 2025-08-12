#!/usr/bin/env python3

import httpx
import pytest

from backend import ollama_client as oc

pytestmark = pytest.mark.unit


class DummyResp:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {"models": [{"name": "cas/mistral-7b-instruct-v0.3:latest"}]}

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
