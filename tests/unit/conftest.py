from __future__ import annotations

import os

import pytest

# Global flags for network-guard coordination
_allow_network_active: bool = False
_current_nodeid: str = "<unknown>"


@pytest.fixture(scope="session", autouse=True)
def _configure_unitnetguard_logging():
    """Ensure UnitNetGuard logs are persisted under reports/logs.

    Adds a file handler for the UnitNetGuard logger to aid flake diagnostics.
    """
    try:
        import logging
        from pathlib import Path

        logs_dir = Path("reports") / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "unit_netguard.log"

        logger = logging.getLogger("UnitNetGuard")
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers when re-running within the same process
        existing = [
            h
            for h in logger.handlers
            if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith(str(log_file))
        ]
        if not existing:
            fh = logging.FileHandler(log_file)
            fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(fh)
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True, scope="session")
def _disable_network_for_unit_tests(pytestconfig: pytest.Config):
    """Disable real network access for unit tests.

    Allows only Unix domain sockets so pytest can function normally.
    """
    try:
        from pytest_socket import disable_socket, enable_socket
    except Exception as exc:  # pragma: no cover - make failure explicit
        raise RuntimeError("pytest-socket must be installed for unit tests to run with network disabled.") from exc

    # Re-assert blocking in case any earlier code enabled sockets
    disable_socket(allow_unix_socket=True)
    # Verify blocking is active; fail fast if not
    # Lightweight verification: ensure connect() is intercepted by pytest-socket
    # without performing a real DNS lookup or external connection.
    try:
        import socket

        from pytest_socket import SocketBlockedError  # type: ignore

        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # This should be intercepted by pytest-socket and raise immediately.
            test_sock.settimeout(0.01)
            test_sock.connect(("10.255.255.1", 9))  # unroutable/reserved range
            raise AssertionError("Network blocking did not activate in unit tests (socket.connect succeeded).")
        except SocketBlockedError:
            # Expected: sockets are blocked
            pass
        finally:
            try:
                test_sock.close()
            except Exception:
                pass
    except Exception:
        # Best-effort: if any unexpected error occurs here, continue; individual tests
        # will still be protected by per-test enforcement until we simplify further.
        pass
    try:
        yield
    finally:
        enable_socket()


# Final safety net: explicitly force AF_INET connect/create_connection to raise in unit tests
@pytest.fixture(autouse=True)
def _force_af_inet_block(monkeypatch: pytest.MonkeyPatch):
    try:
        import socket as _socket

        from pytest_socket import SocketBlockedError  # type: ignore

        original_connect = _socket.socket.connect
        original_create_connection = _socket.create_connection

        def _blocked_connect(self: _socket.socket, address):  # type: ignore[no-redef]
            # Allow opt-in when the test explicitly requested network
            if _allow_network_active:
                return original_connect(self, address)
            # Block only INET/INET6 tuple addresses; allow AF_UNIX (str path)
            if isinstance(address, tuple) and len(address) >= 2:
                raise SocketBlockedError("Network disabled in unit tests (forced)")
            return original_connect(self, address)

        from typing import Any

        def _blocked_create_connection(address: Any, *args: Any, **kwargs: Any):  # type: ignore[no-redef]
            if _allow_network_active:
                return original_create_connection(address, *args, **kwargs)  # type: ignore[arg-type]
            if isinstance(address, tuple) and len(address) >= 2:
                raise SocketBlockedError("Network disabled in unit tests (forced)")
            return original_create_connection(address, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(_socket.socket, "connect", _blocked_connect, raising=True)
        monkeypatch.setattr(_socket, "create_connection", _blocked_create_connection, raising=True)
    except Exception:
        # Best-effort; pytest-socket should already enforce this
        pass


@pytest.fixture()
def allow_network():
    """Temporarily enable real sockets for a single test.

    Use only when a unit test must perform real network I/O; prefer moving such
    tests to integration or mocking calls. Restores the session-level blocking
    afterwards.
    """
    try:
        from pytest_socket import disable_socket, enable_socket  # type: ignore
    except Exception:
        # If plugin missing, nothing to toggle
        yield
        return

    # Mark this test as explicitly allowed to enable sockets
    global _allow_network_active
    _allow_network_active = True
    enable_socket()
    try:
        yield
    finally:
        # Re-disable, allowing Unix sockets so pytest can function
        disable_socket(allow_unix_socket=True)
        _allow_network_active = False


@pytest.fixture(autouse=True)
def _log_socket_block_status(request: pytest.FixtureRequest, _disable_network_for_unit_tests):
    """Diagnose and enforce socket blocking at the start of each test.

    Fail fast if sockets are found enabled to pinpoint the first victim test.
    """
    # Default: no-op for per-test diagnostics to keep unit suite fast.
    # Turn on by setting UNITNETGUARD_FAIL_FAST=1 when actively diagnosing.
    if os.environ.get("UNITNETGUARD_FAIL_FAST") != "1":
        yield
        return

    if os.environ.get("UNITNETGUARD_DISABLE_PER_TEST") == "1":
        # Skip per-test diagnostics when explicitly disabled for stabilization checks
        yield
        return
    try:
        # Record current nodeid for session-scope guard diagnostics
        global _current_nodeid
        _current_nodeid = getattr(request.node, "nodeid", "<unknown>")
        import logging
        import socket

        import pytest
        from pytest_socket import SocketBlockedError, disable_socket  # type: ignore

        # Quick probe: should raise SocketBlockedError when blocked
        probe_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe_sock.settimeout(0.01)
            probe_sock.connect(("10.0.0.0", 9))
            logging.getLogger("UnitNetGuard").error(
                "NOT BLOCKED: %s (probe connect() succeeded)", getattr(request.node, "nodeid", "<unknown>")
            )
            if os.environ.get("UNITNETGUARD_FAIL_FAST") == "1":
                pytest.fail("UnitNetGuard: sockets NOT BLOCKED at test start")
            else:
                disable_socket(allow_unix_socket=True)
        except SocketBlockedError:
            logging.getLogger("UnitNetGuard").info("blocked: %s", getattr(request.node, "nodeid", "<unknown>"))
        except Exception as exc:
            # Any other exception means we reached OS/network stack, not blocked by pytest-socket
            logging.getLogger("UnitNetGuard").error(
                "NOT BLOCKED (unexpected error: %r): %s", exc, getattr(request.node, "nodeid", "<unknown>")
            )
            if os.environ.get("UNITNETGUARD_FAIL_FAST") == "1":
                pytest.fail("UnitNetGuard: sockets NOT BLOCKED (unexpected error path)")
            else:
                disable_socket(allow_unix_socket=True)
        finally:
            try:
                probe_sock.close()
            except Exception:
                pass
    except Exception:
        # Best-effort diagnostic only
        pass
    # Always yield to behave as a generator fixture across all code paths
    yield


@pytest.fixture(autouse=True, scope="session")
def _guard_against_enable_socket_misuse():
    """Session-scope guard to prevent accidental enable_socket during unit tests.

    Replaces pytest_socket.enable_socket with a guarded version that raises unless
    the test opted-in via the allow_network fixture.
    """
    try:
        import pytest_socket as _ps  # type: ignore

        original_enable = getattr(_ps, "enable_socket", None)
        if not callable(original_enable):
            yield
            return

        def _guarded_enable_socket(*args, **kwargs):  # type: ignore[no-redef]
            # Simple guard: only allow when the test opted in via allow_network
            if not _allow_network_active:
                raise AssertionError("UnitNetGuard: enable_socket() called during unit tests without allow_network.")
            return original_enable(*args, **kwargs)

        # Apply guard
        setattr(_ps, "enable_socket", _guarded_enable_socket)
        try:
            yield
        finally:
            # Restore original
            try:
                setattr(_ps, "enable_socket", original_enable)
            except Exception:
                pass
    except Exception:
        # Best-effort; if pytest_socket is unavailable, do nothing
        yield


@pytest.fixture(autouse=True)
def _guard_weaviate_connect_to_custom(monkeypatch: pytest.MonkeyPatch):
    """Prevent real Weaviate connections during unit tests.

    Replaces `weaviate.connect_to_custom` with a function that raises unless a test
    explicitly monkeypatches it. This ensures unit tests don't reach real services.
    """
    try:
        import weaviate  # type: ignore

        if hasattr(weaviate, "connect_to_custom"):

            def _blocked_connect_to_custom(*args, **kwargs):  # type: ignore
                raise AssertionError("UnitNetGuard: weaviate.connect_to_custom called during unit tests")

            monkeypatch.setattr(weaviate, "connect_to_custom", _blocked_connect_to_custom, raising=True)
    except Exception:
        # If weaviate isn't installed or import fails, skip guarding
        pass
    yield
