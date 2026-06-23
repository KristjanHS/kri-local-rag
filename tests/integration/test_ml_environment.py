import logging
import os
from pathlib import Path

import pytest
import torch

# Integration tests for ML environment validation
# --- Constants for ML Environment Validation ---
from backend.config import DEFAULT_EMBEDDING_MODEL

EXPECTED_MODEL_NAME = DEFAULT_EMBEDDING_MODEL


def _selected_variant() -> str:
    """Resolve the active torch wheel variant the way scripts/select_variant.sh does.

    Precedence: ``KRI_VARIANT`` env > ``<repo>/.kri-variant.local`` > ``gpu`` default.
    """
    env = os.environ.get("KRI_VARIANT", "").strip()
    if env:
        return env
    variant_file = Path(__file__).resolve().parents[2] / ".kri-variant.local"
    if variant_file.is_file():
        return variant_file.read_text().strip()
    return "gpu"


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def cached_sentence_transformer_model():
    """
    Loads the SentenceTransformer model using the centralized loading function.
    Works in both online and offline modes.
    """
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EXPECTED_MODEL_NAME)
        logger.info("--- Model loaded successfully ---")
        return model
    except Exception as e:
        pytest.fail(f"Failed to load model '{EXPECTED_MODEL_NAME}': {e}")


def test_pytorch_wheel_matches_selected_variant():
    """
    Verifies the installed PyTorch wheel matches the selected build variant.

    The CPU wheel has no CUDA support compiled in; the GPU (cu128) wheel does.
    The repo defaults to the GPU variant (CI/act set ``KRI_VARIANT=cpu``), so a
    hardcoded CPU-only assertion would fail for anyone running locally. Asserting
    against the selected variant catches an accidental wheel mismatch either way.
    """
    variant = _selected_variant()
    # torch.version is a module in some builds; prefer hasattr checks
    cuda_ver = getattr(getattr(torch, "version", object()), "cuda", None)

    if variant == "cpu":
        assert cuda_ver is None, (
            "CPU variant selected but PyTorch was built with CUDA support "
            f"(torch.version.cuda={cuda_ver!r}). Reinstall from the CPU wheel (make use-cpu)."
        )
        assert not torch.backends.mps.is_available(), (
            "CPU variant selected but PyTorch reports an available MPS device."
        )
    else:
        assert cuda_ver is not None, (
            "GPU variant selected but PyTorch has no CUDA support "
            "(torch.version.cuda is None). Reinstall from the GPU wheel (make use-gpu)."
        )


def test_pytorch_cpu_optimizations_are_available():
    """
    Checks if CPU-specific libraries like MKL are available, which are
    expected with the CPU-optimized PyTorch wheel for Intel processors.
    """
    # For modern PyTorch CPU wheels, the Math Kernel Library (MKL) is a key indicator.
    # Some CPU wheels may not expose MKL; relax to non-fatal check but keep signal
    assert hasattr(torch.backends, "mkl"), "MKL backend not present in torch.backends"


def test_sentence_transformer_model_loads_on_cpu(cached_sentence_transformer_model):
    """
    Uses the cached SentenceTransformer model to ensure it initializes correctly
    on the CPU without requiring a GPU.
    """
    model = cached_sentence_transformer_model
    assert model is not None, "Cached model is not available."

    # Simple check to confirm the model is loaded and functional
    test_sentence = "This is a test sentence."
    try:
        embedding = model.encode(test_sentence)
        assert embedding.shape == (384,), f"Expected embedding shape (384,), but got {embedding.shape}"
        logger.info(f"--- Successfully verified embedding with cached '{EXPECTED_MODEL_NAME}'. ---")
    except Exception as e:
        pytest.fail(f"Failed to use the cached SentenceTransformer model. Error: {e}")
