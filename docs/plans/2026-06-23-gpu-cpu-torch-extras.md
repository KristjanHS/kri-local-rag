# Plan — GPU-primary / CPU-backup torch via uv conflict-extras

> 2026-06-23. Port the `cpu` / GPU mutually-exclusive torch extras pattern from
> `~/projects/stt-faster/` into kri-local-rag. **GPU (cu128) is the default for
> local/bare-metal dev; CPU is the fallback** for CI, `act`, the Docker app image,
> and CPU-only machines. Decisions locked: channel = **cu128**, mechanism =
> **uv conflict-extras (`cpu` / `gpu`)**.

## Why
- `torch` is CPU-index-pinned in base deps; `torchvision` (transitive) comes from PyPI →
  ABI mismatch (`operator torchvision::nms does not exist`) when versions cross.
  Pinning **both** torch + torchvision to one index per extra fixes this *and* enables GPU.
- The app's GPU work today is only Ollama (compose already reserves nvidia). The Streamlit
  app's sentence-transformers (embeddings + cross-encoder rerank, `backend/models.py`) is
  what this change moves to GPU for local dev.

## Key design points (adapted from stt-faster)
- stt-faster defaults to **cpu**; kri defaults to **gpu** (GPU primary). Selector default = `gpu`.
- stt-faster uses `torchaudio`; kri uses `torchvision`.
- App Docker image stays **CPU** (slim runtime, no CUDA base, no nvidia runtime for the app
  service) → its `uv sync` lines pass `--extra cpu`. Putting the app container on GPU would
  need a CUDA base image + nvidia runtime reservation — **out of scope** here.
- `requirements.txt` already excludes torch (`make export-reqs` `--no-emit-package torch`),
  so the dependency-audit path is unaffected; no dual requirements files needed (unlike
  stt-faster's `export-reqs-cpu`/`-cu130`).

## Tasks

### T1 — `pyproject.toml`: extras + conflicts + sources + indexes
- Remove `torch>=2.8.0,<3.0.0` from `[project.dependencies]`.
- Add `[project.optional-dependencies]`:
  ```toml
  cpu = ["torch>=2.8.0,<3.0.0", "torchvision>=0.23.0,<1.0.0"]
  gpu = ["torch>=2.8.0,<3.0.0", "torchvision>=0.23.0,<1.0.0"]
  ```
- `[tool.uv] conflicts = [[{extra="cpu"}, {extra="gpu"}]]`.
- `[tool.uv.sources]`: bind `torch` and `torchvision` each to `{index="pytorch-cpu", extra="cpu"}`
  and `{index="pytorch-cu128", extra="gpu"}`. Drop the old single `torch = {index="pytorch-cpu"}`.
- Add `[[tool.uv.index]]` `pytorch-cu128` (`https://download.pytorch.org/whl/cu128`, `explicit=true`)
  alongside the existing `pytorch-cpu`. Remove the GPU "for GPU:" comments.
- `pillow` etc. constraint-dependencies from Phase A stay as-is.

### T2 — Variant selector machinery (port from stt-faster, rename stt→kri)
- `scripts/select_variant.sh` — read `.kri-variant.local`, validate ∈ {cpu,gpu}, **default `gpu`**.
- `run_uv.sh` — resolve variant, `uv venv --seed`, `uv sync --extra "$VARIANT" --group test "$@"`.
- `.kri-variant.local` → add to `.gitignore` (per-machine, not committed).

### T3 — Makefile
- New targets: `use-gpu` / `use-cpu` (write `.kri-variant.local` + sync), `show-variant`, `sync` (→ `./run_uv.sh`).
- Update existing `uv sync` callsites to pass an extra (default gpu via selector, or explicit):
  - `uv-sync-test` (L69), the two e2e targets (L280, L293) → route through selector or add `--extra`.
- `pip-audit` path unaffected (torch excluded from export).

### T4 — `scripts/dev/setup-dev-env.sh`
- Route bootstrap through `run_uv.sh` (or pass `--extra gpu` default) so a fresh checkout gets GPU.

### T5 — `docker/app.Dockerfile`
- Both `uv sync --locked …` lines (L28 dep-only, L43 project) → add `--extra cpu`.
  (Phase-1 `--no-install-project --no-dev --extra cpu`; phase-2 branches likewise.)

### T6 — CI workflows (`.github/`)
- Every `uv sync` in workflows (and `setup-uv` composite usage) → `--extra cpu`
  (GitHub + `act` runners are CPU-only; must not pull CUDA wheels).

### T7 — Verify
- `make use-cpu && uv sync --extra cpu --group dev --group test --frozen` → `.venv/bin/python -m pytest tests/unit -q` green; assert `torch.__version__` ends `+cpu`.
- `make use-gpu` resolves cu128 in `uv.lock` (resolution only; runtime GPU needs the hardware).
- `uv lock` contains both cpu+gpu with conflict markers; `make export-reqs` still excludes torch.
- `actionlint` on changed workflows.

## Open scope confirmation
- App Docker image stays CPU (above). If the **Dockerized** app should also run torch on GPU,
  that's a separate follow-up (CUDA base image + compose nvidia reservation for the app service).
