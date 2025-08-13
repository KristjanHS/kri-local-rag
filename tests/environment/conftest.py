from __future__ import annotations

import pytest

## No session-wide socket toggling required; sockets are allowed by default in non-unit suites.


@pytest.fixture(autouse=True)
def _temporarily_enable_network_for_environment_tests():
    """Temporarily enable sockets for each environment test only.

    Restores socket blocking after each test to avoid leaking state to other suites.
    """
    try:
        from pytest_socket import disable_socket, enable_socket  # type: ignore

        enable_socket()
        try:
            yield
        finally:
            disable_socket(allow_unix_socket=True)
    except Exception:
        yield
