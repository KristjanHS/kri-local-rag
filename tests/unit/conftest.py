from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _disable_network_for_unit_tests() -> None:
    """Block real sockets for unit tests; allow Unix sockets for pytest internals."""
    from pytest_socket import disable_socket

    disable_socket(allow_unix_socket=True)


@pytest.fixture(autouse=True)
def _enforce_blocked_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure low-level socket operations raise in unit tests.

    Reinforces pytest-socket by guarding both socket.socket.connect and
    socket.create_connection against INET/INET6 addresses.
    """
    import socket as _socket

    from pytest_socket import SocketBlockedError

    original_connect = _socket.socket.connect
    original_create_connection = _socket.create_connection

    def _blocked_connect(self: _socket.socket, address):  # type: ignore[no-redef]
        if isinstance(address, tuple) and len(address) >= 2:
            raise SocketBlockedError("Network disabled in unit tests (connect)")
        return original_connect(self, address)

    from typing import Any

    def _blocked_create_connection(address: Any, *args, **kwargs):  # type: ignore[no-redef]
        # Only block if address is a tuple of length 2 and matches (str|None, int)
        if (
            isinstance(address, tuple)
            and len(address) == 2
            and (isinstance(address[0], (str, type(None))) and isinstance(address[1], int))
        ):
            raise SocketBlockedError("Network disabled in unit tests (create_connection)")
        return original_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(_socket.socket, "connect", _blocked_connect, raising=True)
    monkeypatch.setattr(_socket, "create_connection", _blocked_create_connection, raising=True)


from unittest.mock import MagicMock


@pytest.fixture
def mock_embedding_model(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Fixture to mock the SentenceTransformer, preventing model downloads."""
    mock = MagicMock()
    monkeypatch.setattr("backend.retriever.SentenceTransformer", mock)
    return mock


@pytest.fixture
def managed_cross_encoder(mocker):
    """Fixture to mock the CrossEncoder class, returning a MagicMock instance."""
    mock_encoder_instance = MagicMock()
    mocker.patch("sentence_transformers.CrossEncoder", return_value=mock_encoder_instance)
    yield mock_encoder_instance
