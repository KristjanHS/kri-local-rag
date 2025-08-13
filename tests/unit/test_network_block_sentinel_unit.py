import socket

import pytest
from pytest_socket import SocketBlockedError


def test_network_block_sentinel():
    with pytest.raises(SocketBlockedError):
        # This should be intercepted by pytest-socket without reaching OS
        socket.create_connection(("example.com", 80), timeout=0.01)
