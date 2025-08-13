from __future__ import annotations

import types

import pytest

pytestmark = pytest.mark.unit


def test_weaviate_connect_to_custom_guard_blocks_real_client():
    """Direct calls to weaviate.connect_to_custom must be blocked in unit tests."""
    import weaviate  # type: ignore

    with pytest.raises(AssertionError):
        weaviate.connect_to_custom(  # type: ignore[attr-defined]
            http_host="localhost",
            http_port=8080,
            grpc_host="localhost",
            grpc_port=50051,
            http_secure=False,
            grpc_secure=False,
        )


def test_weaviate_connect_to_custom_can_be_patched_in_test(monkeypatch: pytest.MonkeyPatch):
    """Tests may override the guard by explicitly monkeypatching the connector."""
    import weaviate  # type: ignore

    sentinel_client = types.SimpleNamespace(name="fake-weaviate-client")

    def _fake_connect_to_custom(*_args, **_kwargs):  # type: ignore[no-redef]
        return sentinel_client

    # Override the unit-level guard for this test only
    monkeypatch.setattr(weaviate, "connect_to_custom", _fake_connect_to_custom, raising=True)

    client = weaviate.connect_to_custom(  # type: ignore[attr-defined]
        http_host="localhost",
        http_port=8080,
        grpc_host="localhost",
        grpc_port=50051,
        http_secure=False,
        grpc_secure=False,
    )

    assert client is sentinel_client
