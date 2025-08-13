import socket

import pytest
from pytest_socket import SocketBlockedError


def test_network_block_sentinel():
    with pytest.raises(SocketBlockedError):
        # This should be intercepted by pytest-socket without reaching OS
        socket.create_connection(("10.255.255.1", 9), timeout=0.05)
