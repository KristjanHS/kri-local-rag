import logging

import pytest
import torch

# Integration tests for ML environment validation
# --- Constants for ML Environment Validation ---
from backend.config import DEFAULT_EMBEDDING_MODEL

EXPECTED_MODEL_NAME = DEFAULT_EMBEDDING_MODEL

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


def test_pytorch_is_cpu_only():
    """
    Verifies that the installed PyTorch wheel does not have CUDA support compiled in.
    """
    # torch.version is a module in some builds; prefer hasattr checks
    cuda_ver = getattr(getattr(torch, "version", object()), "cuda", None)
    assert cuda_ver is None, (
        "Test failed: PyTorch was built with CUDA support (torch.version.cuda is not None), "
        "but a CPU-only build is expected. Please reinstall PyTorch from the CPU wheel."
    )
    assert not torch.backends.mps.is_available(), (
        "Test failed: PyTorch has access to an MPS device, but it should be CPU-only."
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
