# Design: Simplify the CPU/GPU torch variant scheme

**Date:** 2026-06-23
**Status:** Approved design (not yet implemented — ready for `/impag` in a fresh session)
**Supersedes:** the conflict-extras variant scheme from `docs/plans/archive/2026-06-23-gpu-cpu-torch-extras.md`

## Goal

Replace the dual conflicting-extras (`cpu`/`gpu`) torch scheme with the simplest
design that still gives **working local GPU torch** and a **slim CPU build for
CI and the Docker app image**.

Driven by two confirmed facts from the 2026-06-23 debugging session:

1. **GPU is a hard requirement** for local bare-metal dev (sentence-transformers
   embeddings/reranking on CUDA). The Docker app image is already CPU-only — only
   Ollama uses the GPU there — so GPU torch matters *only* on the dev host.
2. **The no-extra PyPI torch already gives working CUDA.** `torch` resolved from
   PyPI (currently `2.12.1+cu130`, and the gpu-extra `2.11.0+cu128`) imports
   fine, `torch.cuda.is_available()==True`, and `torchvision.ops.nms` works on
   both CPU and CUDA. The `torchvision::nms` ABI error that originally motivated
   the index-pinned extras only occurs when torch and torchvision come from
   *different* sources; taking both from the **same** source (PyPI default, or
   the cpu index together) keeps the ABI matched. The user accepts "whatever CUDA
   the default PyPI wheel ships" (no need to pin a specific cu1xx channel).

These mean the entire `gpu` extra + `pytorch-cu128` index + conflict machinery is
unnecessary, and the variant-*selection* layer can be deleted outright.

## Chosen approach — GPU-default, single CPU opt-in extra

Mental model collapses to:

- **Local dev:** do nothing → `make sync` installs the default (PyPI) torch → GPU.
- **CI / Docker:** pass `--extra cpu` → slim `+cpu` wheels from the pytorch-cpu index.

The word "variant" disappears from day-to-day use; there is just "the default"
and "add `--extra cpu`".

### Why A over the alternatives

| Approach | Complexity | Time | Risk | Extensibility | Alignment |
|---|:--:|:--:|:--:|:--:|:--:|
| **A — GPU-default + CPU extra (chosen)** | 2 | 2 | 2 | 4 | 5 |
| C — single torch, no extras (CUDA everywhere) | 1 | 1 | 3 | 3 | 2 |
| Status quo (post-fix dual extras) | 5 | 1 | 2 | 3 | 4 |

- **C** is marginally simpler but ships ~2 GB of unused CUDA libs into the Docker
  app image and slows CI installs — it violates the deliberate "slim CPU Docker"
  decision. Rejected.
- **Status quo** works (after the run_uv.sh fix in `c8035ba`) but keeps a fragile
  design whose incremental cu13↔cu12 swaps corrupt the shared `nvidia/` namespace.
  Rejected in favour of removing the failure mode entirely.

## Design details

### `pyproject.toml`
- **Move `torch` + `torchvision` back into `[project.dependencies]`** (base deps).
  The default resolution pulls them from PyPI → GPU-capable, ABI-matched.
- **Keep a single `cpu` extra** that re-pins both to the CPU index:
  ```toml
  [project.optional-dependencies]
  cpu = ["torch>=2.8.0,<3.0.0", "torchvision>=0.23.0,<1.0.0"]

  [[tool.uv.index]]
  name = "pytorch-cpu"
  url = "https://download.pytorch.org/whl/cpu"
  explicit = true

  [tool.uv.sources]
  torch       = [{ index = "pytorch-cpu", extra = "cpu" }]
  torchvision = [{ index = "pytorch-cpu", extra = "cpu" }]
  ```
- **Delete:** the `gpu` extra, the `[[tool.uv.index]] pytorch-cu128` block, the
  `[tool.uv].conflicts` block, and all gpu source bindings.
- Keep the `torchvision` deptry `DEP002` ignore (still an ABI peer, not imported
  directly by first-party code).

### Tooling — delete the selection layer
- **Remove:** `scripts/select_variant.sh`, `.kri-variant.local` (stop using;
  it is gitignored), the `KRI_VARIANT` env override, and the `.venv/.kri-variant`
  marker logic added in `c8035ba`.
- **`run_uv.sh`** shrinks to: keep uv self-update + venv-exists guard, then
  `uv sync --group test "$@"` and the `.venv/bin/python -V` sanity print. No
  variant resolution, no clean-recreate-on-switch (there is no switch).
- **`Makefile`:** remove `use-gpu` / `use-cpu` / `show-variant`; `sync` just
  calls `./run_uv.sh`. The `pre-commit` / `yamlfmt` targets drop the
  `V=$(./scripts/select_variant.sh)` line and sync without an extra (or with
  `--extra cpu` only if a slim env is wanted there — default: no extra).

### CI / Docker
- **4 CI workflows** that set `KRI_VARIANT: cpu`: replace with an explicit
  `--extra cpu` on the `uv sync` invocation (clearer than an env indirection).
- **`docker/app.Dockerfile`:** already syncs `--extra cpu` — unchanged.
- **`requirements.txt` export:** still `--no-emit-package torch torchvision` so
  the Trivy FS scan path stays torch-free.

## Implementation validation checklist

Run these during `/impag`; each is a potential gotcha, not a blocker:

1. `uv lock` resolves cleanly with torch/torchvision in base deps + a single
   `extra = "cpu"` source-override and **no** `conflicts` block.
2. Default (no-extra) sync installs torchvision and `torchvision.ops.nms` works
   on CPU and CUDA (re-verify; confirmed for cu128/cu130 on 2026-06-23).
3. `uv sync --extra cpu` yields `+cpu` wheels (slim, no nvidia-* libs) and
   `torch.cuda.is_available()==False`.
4. `deptry` and `make export-reqs` unaffected (torchvision DEP002 ignore stays;
   export still excludes torch + torchvision).
5. 65 unit tests green on the default env; pyright clean.

## Out of scope

- Pinning a specific CUDA channel (user accepts the PyPI default; floats with
  torch releases).
- Any change to Ollama GPU usage (independent of torch).
- The shipped `c8035ba` run_uv.sh fix is largely mooted by this design but stays
  in history; this design removes the code paths it patched.
