"""Regression guard for the torchvision-stub / transformers import chain.

The CrossEncoder load path broke when ``backend.models``' text-only torchvision stub
shadowed a working torchvision: transformers 5.x imports ``torchvision.io.ImageReadMode``
during ``PreTrainedModel`` import, which the fail-fast stub rejected. That surfaced as a
misleading "sentence-transformers not available" error in the GUI.

These tests exercise the exact import chain that broke without downloading any model, so
they run in the fast unit gate (network-blocked) rather than the slow integration suite.
"""

import importlib.util

import pytest


def test_backend_models_import_does_not_break_cross_encoder_import():
    """Importing backend.models must not break the sentence-transformers import path."""
    # Importing backend.models runs the torchvision-stub setup at module load time.
    import backend.models

    assert backend.models is not None

    # The exact import that failed in the GUI: transformers 5.x touches
    # torchvision.io.ImageReadMode here. Must succeed whether torchvision is real
    # (not clobbered) or stubbed (stub now provides a benign ImageReadMode).
    from sentence_transformers.cross_encoder import CrossEncoder

    assert CrossEncoder is not None


def test_real_torchvision_not_clobbered_when_available():
    """When torchvision is installed, backend.models must not replace it with the stub."""
    if importlib.util.find_spec("torchvision") is None:
        pytest.skip("torchvision not installed in this environment")

    import backend.models
    import torchvision

    assert backend.models is not None
    assert "<stub:" not in getattr(torchvision, "__file__", ""), (
        "backend.models must not shadow a real torchvision with the text-only stub"
    )
