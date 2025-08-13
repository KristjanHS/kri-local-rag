from __future__ import annotations

import socket

import pytest


def test_block_external_network_low_level():
    # Directly verify sockets are disabled to avoid interference from other monkeypatches
    from pytest_socket import SocketBlockedError  # type: ignore

    with pytest.raises(SocketBlockedError):
        socket.create_connection(("example.com", 80), timeout=0.5)
