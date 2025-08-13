import os
import sys
import types


def test_cross_encoder_enables_heavy_optimizations_when_allowed(monkeypatch):
    os.environ["RERANKER_CROSS_ENCODER_OPTIMIZATIONS"] = "true"

    if "backend.qa_loop" in sys.modules:
        del sys.modules["backend.qa_loop"]
    import backend.qa_loop as qa_loop

    qa_loop_sys = types.SimpleNamespace(modules={})
    monkeypatch.setattr(qa_loop, "sys", qa_loop_sys, raising=True)

    class FakeCE:
        def __init__(self, name):
            self.name = name

        def predict(self, pairs):
            return [0.0] * len(pairs)

    monkeypatch.setattr(qa_loop, "CrossEncoder", FakeCE, raising=True)

    class FakeTorch:
        def __init__(self):
            self.num_threads = None
            self.compile_called = False

        def set_num_threads(self, n):
            self.num_threads = n

    fake_torch = FakeTorch()

    def fake_compile(model, backend=None, mode=None):
        fake_torch.compile_called = True
        setattr(model, "_compiled_backend", backend)
        setattr(model, "_compiled_mode", mode)
        return model

    setattr(fake_torch, "compile", fake_compile)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    encoder = qa_loop._get_cross_encoder("dummy-model")

    assert isinstance(encoder, FakeCE)
    assert getattr(encoder, "_compiled_backend", None) == "inductor"
    assert getattr(encoder, "_compiled_mode", None) == "max-autotune"
    assert fake_torch.compile_called is True
    assert fake_torch.num_threads == 12
