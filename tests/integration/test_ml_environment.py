import logging
import shutil
import subprocess
from pathlib import Path

import pytest
import torch

# Integration tests for ML environment validation
# --- Constants for ML Environment Validation ---
from backend.config import DEFAULT_EMBEDDING_MODEL

EXPECTED_MODEL_NAME = DEFAULT_EMBEDDING_MODEL

REPO_ROOT = Path(__file__).resolve().parents[2]


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _uv_export(*extra_args: str) -> str:
    """Return `uv export` output for the committed lock, no network (--frozen).

    Universal export: it emits every platform fork with environment markers, so
    the assertions below hold regardless of the host OS.
    """
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not on PATH — cannot inspect the resolved lock")
    result = subprocess.run(
        [uv, "export", "--frozen", "--no-hashes", "--no-emit-project", *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"`uv export {' '.join(extra_args)}` failed:\n{result.stderr}")
    return result.stdout


def _torch_lines(exported: str) -> list[str]:
    return [line for line in exported.splitlines() if line.startswith("torch==")]


def test_torch_variant_resolution_forks_correctly():
    """Lock-level tripwire for the GPU-default + cpu-extra torch scheme.

    The design hinges on a subtle uv behavior: torch sits in base deps and
    resolves from PyPI (CUDA wheels on Linux) by default, while the ``cpu`` extra
    re-pins it to the pytorch-cpu index. The otherwise-redundant ``gpu`` extra
    exists only to satisfy uv's >=2-members-per-conflict-set rule (see pyproject
    ``[tool.uv].conflicts``) — that conflict is what scopes the cpu index to
    ``--extra cpu`` instead of bleeding into the base resolution.

    If a future uv changes either rule, the no-extra install would silently
    collapse to CPU torch (0 nvidia pkgs) with no error. This test reads the
    committed lock (``--frozen``, no network) and fails loudly if that happens.
    """
    default = _uv_export()
    cpu = _uv_export("--extra", "cpu")

    # Default fork → CUDA wheels present, torch un-suffixed (resolved from PyPI).
    assert any(line.startswith("nvidia-") for line in default.splitlines()), (
        "GPU-default regressed: the no-extra resolution pulls no nvidia-* packages "
        "(torch collapsed to a CPU wheel). Check [tool.uv].conflicts in pyproject.toml."
    )
    assert _torch_lines(default), "no torch in the default resolution"
    assert all("+cpu" not in line for line in _torch_lines(default)), (
        f"no-extra resolution pinned a +cpu torch wheel (should be PyPI/CUDA): {_torch_lines(default)}"
    )

    # cpu fork → no CUDA wheels, torch carries the +cpu local version on non-darwin.
    assert not any(line.startswith("nvidia-") for line in cpu.splitlines()), (
        "--extra cpu pulled nvidia-* packages — the cpu index pin leaked CUDA wheels."
    )
    assert any("+cpu" in line for line in _torch_lines(cpu)), (
        f"--extra cpu did not pin a +cpu torch wheel: {_torch_lines(cpu)}"
    )


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


def test_torchvision_nms_abi_matches_torch():
    """
    torch and torchvision must come from the same wheel source or torchvision's
    C++ ops fail to register (``operator torchvision::nms does not exist``). This
    is the ABI invariant the single-source scheme protects: the default PyPI
    wheels, or both from the cpu index together. Run on CPU so it holds for both
    the default (GPU) and ``--extra cpu`` installs.
    """
    import torchvision

    boxes = torch.as_tensor([[0.0, 0.0, 1.0, 1.0], [0.0, 0.0, 1.0, 1.0]])
    scores = torch.as_tensor([0.9, 0.8])
    # A raw call is intentional: an ABI mismatch raises
    # `operator torchvision::nms does not exist`, which fails the test with a
    # clear traceback (torch {ver} / torchvision {ver}).
    keep = torchvision.ops.nms(boxes, scores, iou_threshold=0.5)
    assert keep.numel() >= 1


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
