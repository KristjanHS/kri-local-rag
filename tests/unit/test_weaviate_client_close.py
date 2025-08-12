import types

import pytest

import backend.qa_loop as qa_loop


@pytest.mark.unit
def test_ensure_weaviate_ready_and_populated_closes_client(monkeypatch):
    class FakeCollections:
        def exists(self, name: str) -> bool:
            return True

    class FakeClient:
        def __init__(self):
            self.closed = False

        def is_ready(self):
            return True

        @property
        def collections(self):
            return FakeCollections()

        def is_connected(self) -> bool:
            return True

        def close(self) -> None:
            self.closed = True

    fake_client = FakeClient()

    def fake_connect_to_custom(**kwargs):  # type: ignore[no-redef]
        return fake_client

    # Monkeypatch the weaviate connection factory used by the function
    monkeypatch.setattr(qa_loop, "weaviate", types.SimpleNamespace(connect_to_custom=fake_connect_to_custom))

    # Run the function under test
    qa_loop.ensure_weaviate_ready_and_populated()

    # Verify client was closed in the finally block
    assert fake_client.closed is True
