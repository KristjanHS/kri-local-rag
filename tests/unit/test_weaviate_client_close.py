import backend.qa_loop as qa_loop


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

    # Monkeypatch the centralized weaviate client getter used by the function
    monkeypatch.setattr("backend.weaviate_client.get_weaviate_client", lambda: fake_client, raising=True)
    # Ensure the wrapper cache points at our fake so the wrapper's closer closes it
    monkeypatch.setattr("backend.weaviate_client._client", fake_client, raising=True)

    # Run the function under test
    qa_loop.ensure_weaviate_ready_and_populated()

    # Verify client was closed in the finally block
    assert fake_client.closed is True
