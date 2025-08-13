from __future__ import annotations

import httpx


def test_httpx_mock_transport_basic():
    # Best practice: use MockTransport for deterministic unit tests instead of relying on global socket blocking
    def handler(request: httpx.Request) -> httpx.Response:  # type: ignore
        assert request.url.host == "example.com"
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, timeout=0.1) as client:
        resp = client.get("http://example.com")
        assert resp.status_code == 200
        assert resp.text == "ok"
