from __future__ import annotations

import pytest

## No session-wide socket toggling required; sockets are allowed by default in non-unit suites.


@pytest.fixture(autouse=True)
def _noop_environment_network_fixture():
    # Sockets are allowed by default in non-unit suites
    yield
