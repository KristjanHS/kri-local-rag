import pytest
import torch

# Try to import CrossEncoder and skip the new test if it's not available.
try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None


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
    assert (
        torch.backends.mkl.is_available()
    ), "Test failed: The MKL backend is not available. This indicates the CPU-optimized wheel may not be in use."


def test_sentence_transformer_model_loads_on_cpu():
    """

    Attempts to load the actual SentenceTransformer model to ensure it
    initializes correctly on the CPU without requiring a GPU.
    This is a critical integration test for the ML environment.
    """
    from sentence_transformers import SentenceTransformer

    try:
        print(
            f"--- About to download and load '{EXPECTED_MODEL_NAME}'. "
            f"This is a one-time operation and may take a few minutes... ---"
        )
        model = SentenceTransformer(EXPECTED_MODEL_NAME, device="cpu")

        # Simple check to confirm the model is loaded and functional
        test_sentence = "This is a test sentence."
        embedding = model.encode(test_sentence)
        assert embedding.shape == (384,), f"Expected embedding shape (384,), but got {embedding.shape}"
        print(f"--- Successfully loaded '{EXPECTED_MODEL_NAME}' and verified embedding. ---")

    except Exception as e:
        pytest.fail(
            f"Failed to load or use SentenceTransformer model '{EXPECTED_MODEL_NAME}' on CPU. "
            f"This is a critical failure for the ML environment. Error: {e}"
        )


@pytest.mark.skipif(CrossEncoder is None, reason="sentence_transformers library not installed.")
def test_torch_compile_on_cross_encoder():
    """
    Verifies that torch.compile can successfully compile the production CrossEncoder model.
    This is a critical integration test to catch environment-specific issues with
    torch.compile, such as the ones that can occur inside a Docker container.
    """
    model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    print(f"--- Loading CrossEncoder model for torch.compile test: {model_name} ---")

    try:
        # 1. Load the actual CrossEncoder model used in production
        model = CrossEncoder(model_name)

        # 2. Set thread count to match production environment
        torch.set_num_threads(12)

        # 3. Compile the model using production settings
        print("--- Compiling model with backend='inductor' and mode='max-autotune'... ---")
        compiled_model = torch.compile(model, backend="inductor", mode="max-autotune")
        print("--- ✓ Model compiled successfully. ---")

        # 4. Create some sample input data
        sentence_pairs = [
            ("What is the capital of France?", "Paris is the capital of France."),
            ("What is the capital of France?", "London is a large city in the UK."),
        ]

        # 5. Run prediction with the compiled model
        with torch.no_grad():
            scores = compiled_model.predict(sentence_pairs)

        # 6. Check that the output is as expected
        assert len(scores) == 2
        assert scores[0] > scores[1]  # The first pair should be more relevant.

        print(f"--- ✓ Compiled model successfully produced scores: {scores} ---")

    except Exception as e:
        pytest.fail(f"torch.compile failed on the CrossEncoder model: {e}")
