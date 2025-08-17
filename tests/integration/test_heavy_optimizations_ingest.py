#!/usr/bin/env python3
"""Integration test: verify heavy torch optimizations are used during ingestion.

This test verifies that backend.ingest applies torch.compile with the intended
CPU settings and runs a minimal ingestion flow using a mocked Weaviate client.
"""

import sys
import types


class _FakeTorch:
    def __init__(self):
        self.num_threads = None
        self.compile_called = False
        self.compile_args = None

    def set_num_threads(self, n):  # not used by ingest.py, but present for parity
        self.num_threads = n

    def compile(self, model, backend=None, mode=None):  # type: ignore[override]
        self.compile_called = True
        self.compile_args = {"backend": backend, "mode": mode}
        # Return the model unchanged to keep pipeline working
        # Attach flags for later assertions
        setattr(model, "_compiled_backend", backend)
        setattr(model, "_compiled_mode", mode)
        return model


class _FakeSentenceTransformer:
    def __init__(self, name):
        self.name = name

    def encode(self, text):
        # Return a fixed-size vector (MiniLM outputs 384 dims).
        return [0.0] * 384


class _FakeBatchCtx:
    def __init__(self, collection):
        self.collection = collection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add_object(self, properties=None, uuid=None, vector=None):  # noqa: D401
        # Collect stats; simulate successful enqueue
        self.collection._added.append(
            {
                "properties": properties,
                "uuid": uuid,
                "vector": vector,
            }
        )


class _FakeCollection:
    def __init__(self):
        self._added = []

        class _Batch:
            def __init__(self, owner):
                self._owner = owner

            def dynamic(self):
                return _FakeBatchCtx(collection=self._owner)

        self.batch = _Batch(self)


class _FakeClient:
    def __init__(self):
        self.collections = types.SimpleNamespace(
            _collections={},
            exists=lambda name: name in self.collections._collections,
            create=self._create,
            get=self._get,
        )

    def _create(self, name, vector_config=None):  # noqa: ARG002
        self.collections._collections[name] = _FakeCollection()
        return self.collections._collections[name]

    def _get(self, name):
        return self.collections._collections.setdefault(name, _FakeCollection())

    def close(self):
        pass


def test_ingestion_uses_torch_compile_with_cpu_optimizations(tmp_path, monkeypatch):
    # Arrange fake torch and sentence_transformers before importing ingest
    fake_torch = _FakeTorch()
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    fake_st_mod = types.ModuleType("sentence_transformers")
    setattr(fake_st_mod, "SentenceTransformer", _FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st_mod)

    # Ensure we import a fresh backend.ingest that sees our fakes
    if "backend.ingest" in sys.modules:
        del sys.modules["backend.ingest"]
    import backend.ingest as ingest  # type: ignore  # re-import with fakes

    # Prepare minimal data directory with a markdown file
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "doc.md").write_text("Hello world. This is a small test.", encoding="utf-8")

    # Use a fake Weaviate client to avoid starting containers
    fake_client = _FakeClient()

    # Act: run ingestion
    ingest.ingest(directory=str(data_dir), collection_name="TestCollectionOptimized", client=fake_client)  # type: ignore[arg-type]

    # Assert: torch.compile was called with expected settings
    assert fake_torch.compile_called is True
    assert fake_torch.compile_args == {"backend": "inductor", "mode": "max-autotune"}

    # Assert: collection received objects
    collection = fake_client.collections.get("TestCollectionOptimized")
    assert isinstance(collection, _FakeCollection)
    assert len(collection._added) >= 1
