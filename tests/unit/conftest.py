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
def mock_embedding_model(mocker) -> MagicMock:
    """Fixture to mock the SentenceTransformer, preventing model downloads."""
    mock = MagicMock()
    # Patch at the retriever level where load_embedder is actually called
    mocker.patch("backend.retriever.load_embedder", return_value=mock)
    return mock


@pytest.fixture
def managed_cross_encoder(mocker):
    """Fixture to mock the CrossEncoder class, returning a MagicMock instance."""
    mock_encoder_instance = MagicMock()
    mocker.patch("sentence_transformers.CrossEncoder", return_value=mock_encoder_instance)
    yield mock_encoder_instance


@pytest.fixture(autouse=True)
def reset_embedding_model_cache():
    """Reset the embedding model cache before each test to prevent state leakage."""
    from backend import retriever

    retriever._embedding_model = None


# ---------------------------------------------------------------------------
# Unit-only Weaviate client fakes and cache hygiene
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_weaviate_client_default(monkeypatch: pytest.MonkeyPatch):
    """Provide a minimal fake Weaviate client for unit tests by default.

    Tests that need custom behavior can still patch
    `backend.weaviate_client.get_weaviate_client` or
    `backend.retriever.get_weaviate_client` and will override this.
    """

    class _FakeQuery:
        def hybrid(self, *args, **kwargs):  # noqa: D401
            class _Res:
                objects = []

            return _Res()

        def bm25(self, *args, **kwargs):  # noqa: D401, pragma: no cover
            class _Res:
                objects = []

            return _Res()

    class _FakeCollection:
        def __init__(self):
            self.query = _FakeQuery()

    class _FakeCollections:
        def __init__(self):
            self._existing = set()

        def exists(self, name):  # noqa: D401
            return name in self._existing

        def get(self, _name):  # noqa: D401
            return _FakeCollection()

    class _FakeWeaviateClient:
        def __init__(self):
            self.collections = _FakeCollections()
            self._closed = False

        def close(self):  # noqa: D401
            self._closed = True

    def _fake_get_client():
        return _FakeWeaviateClient()

    # Patch the centralized wrapper
    import backend.weaviate_client as _wc

    monkeypatch.setattr(_wc, "get_weaviate_client", _fake_get_client, raising=False)

    # Ensure retriever uses the wrapper indirection so tests can patch wrapper
    import backend.retriever as _retriever_mod

    def _shim_retriever_get_client():
        from backend import weaviate_client as __wc

        return __wc.get_weaviate_client()

    monkeypatch.setattr(_retriever_mod, "get_weaviate_client", _shim_retriever_get_client, raising=False)

    # Ensure qa_loop uses the wrapper indirection as well
    try:
        import backend.qa_loop as _qa_loop_mod

        def _shim_qa_get_client():
            from backend import weaviate_client as __wc

            return __wc.get_weaviate_client()

        monkeypatch.setattr(_qa_loop_mod, "get_weaviate_client", _shim_qa_get_client, raising=False)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _clear_weaviate_wrapper_cache():
    """Clear the centralized wrapper client cache before and after each unit test."""
    try:
        from backend.weaviate_client import close_weaviate_client

        close_weaviate_client()
        yield
        close_weaviate_client()
    except Exception:
        # If the module isn't importable in some unit contexts, just continue
        yield


@pytest.fixture(autouse=True)
def _guard_weaviate_connect_to_custom(monkeypatch: pytest.MonkeyPatch):
    """Block direct weaviate.connect_to_custom usage in unit tests by default.

    Individual tests can override by monkeypatching the same attribute.
    """
    try:
        import weaviate  # type: ignore

        def _raise_connect_to_custom(*_args, **_kwargs):  # type: ignore[no-redef]
            raise AssertionError(
                "This test must not create real Weaviate clients. Patch 'weaviate.connect_to_custom' or the wrapper."
            )

        monkeypatch.setattr(weaviate, "connect_to_custom", _raise_connect_to_custom, raising=False)
    except Exception:
        pass
