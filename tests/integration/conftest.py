#!/usr/bin/env python3
"""Fixtures for integration tests."""

from __future__ import annotations


## No socket toggling needed for integration suite; sockets are allowed by default.
## Tests that require Docker compose should depend on the `docker_services` fixture explicitly.


## Removed session-wide compose autostart; rely on explicit docker_services usage in tests that need it.
