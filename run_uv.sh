#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install from https://astral.sh/uv" >&2
  exit 1
fi

# Keep local uv on the latest release so it matches CI (astral-sh/setup-uv@v6
# pins no version, i.e. always latest). Non-fatal: self-update needs network and
# only works for the standalone installer (not pip/pipx/brew installs). Set
# KRI_SKIP_UV_UPDATE=1 to skip (offline, or package-manager-managed uv).
if [ -z "${KRI_SKIP_UV_UPDATE:-}" ]; then
  uv self update || echo "[kri-local-rag] uv self update skipped (offline or non-standalone install)" >&2
fi

# Create the venv if missing. Guard on directory existence rather than running an
# unconditional `uv venv --seed`, which exits non-zero on an existing venv (it
# wants --clear) and would abort this script under `set -e` on every re-run.
if [ ! -d .venv ]; then
  uv venv --seed
fi

# Fallback: if pip is missing for any reason, try ensurepip
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  .venv/bin/python -m ensurepip --upgrade || true
fi

# Sync the project + test group. The default (no extra) pulls the PyPI torch
# wheel (GPU-capable on Linux) for local dev. Pass `--extra cpu` via "$@" for
# slim CPU-only wheels (CI / the Docker app image).
uv sync --group test "$@"

# Quick sanity print via the venv interpreter (not `uv run`, which would re-sync).
.venv/bin/python -V
echo "Env ready. Use '.venv/bin/<cmd>'. Add '--extra cpu' for CPU-only torch wheels."
