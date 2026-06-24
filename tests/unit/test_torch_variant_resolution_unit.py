import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _uv_export(*extra_args: str) -> str:
    """Return `uv export` output for the committed lock, no network (--frozen).

    Output is scoped to the host platform: it emits each extra-fork but only the
    current OS's wheels (nvidia-* carry `sys_platform == 'linux'`, the cpu-fork
    torch line is `+cpu` only on non-darwin). The GPU-default assertions below
    are therefore Linux-shaped — the caller guards with `skipif(darwin)`.
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


@pytest.mark.skipif(
    sys.platform == "darwin",
    reason="GPU-default invariant is Linux-shaped: macOS PyPI torch is CPU-only (no CUDA wheels), "
    "and uv export is host-scoped so the nvidia-/+cpu assertions don't apply.",
)
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
