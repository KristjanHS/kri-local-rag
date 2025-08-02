import pytest
import torch

# --- Constants for ML Environment Validation ---
EXPECTED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def test_pytorch_is_cpu_only():
    """
    Verifies that the installed PyTorch wheel does not have CUDA support compiled in.
    """
    assert torch.version.cuda is None, (
        "Test failed: PyTorch was built with CUDA support (torch.version.cuda is not None), "
        "but a CPU-only build is expected. Please reinstall PyTorch from the CPU wheel."
    )
    assert (
        not torch.backends.mps.is_available()
    ), "Test failed: PyTorch has access to an MPS device, but it should be CPU-only."


def test_pytorch_cpu_optimizations_are_available():
    """
    Checks if CPU-specific libraries like MKL are available, which are
    expected with the CPU-optimized PyTorch wheel for Intel processors.
    """
    # For modern PyTorch CPU wheels, the Math Kernel Library (MKL) is a key indicator.
    assert torch.backends.mkl.is_available(), (
        "Test failed: The MKL backend is not available. " "This indicates the CPU-optimized wheel may not be in use."
    )


def test_sentence_transformer_model_loads_on_cpu():
    """

    Attempts to load the actual SentenceTransformer model to ensure it
    initializes correctly on the CPU without requiring a GPU.
    This is a critical integration test for the ML environment.
    """
    from sentence_transformers import SentenceTransformer

    print(f"--- Loading '{EXPECTED_MODEL_NAME}' for the first time. This may take a moment... ---")
    try:
        model = SentenceTransformer(EXPECTED_MODEL_NAME, device="cpu")

        # Simple check to confirm the model is loaded and functional
        test_sentence = "This is a test sentence."
        embedding = model.encode(test_sentence)

        assert embedding.shape[0] > 0, "Test failed: The loaded model failed to produce a valid embedding."

    except Exception as e:
        pytest.fail("Test failed: Could not load or use the SentenceTransformer model on the CPU. " f"Error: {e}")
