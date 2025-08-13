from __future__ import annotations

import pytest


def test_httpx_get_is_blocked_by_pytest_socket():
    import httpx
    from pytest_socket import SocketBlockedError  # type: ignore

    with pytest.raises(SocketBlockedError):
        # Any real network attempt should be blocked by pytest-socket
        httpx.get("http://example.com", timeout=0.1)
