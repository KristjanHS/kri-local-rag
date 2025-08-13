from __future__ import annotations

import socket

import pytest


def test_block_external_network_low_level():
    # Directly verify sockets are disabled to avoid interference from other monkeypatches
    from pytest_socket import SocketBlockedError  # type: ignore

    with pytest.raises(SocketBlockedError):
        # Use an IP literal to avoid DNS variability; pytest-socket should intercept before OS
        socket.create_connection(("10.255.255.1", 9), timeout=0.5)
