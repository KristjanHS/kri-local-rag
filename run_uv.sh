#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install from https://astral.sh/uv" >&2
  exit 1
fi

# Resolve the per-machine uv extras variant (cpu | gpu) via
# scripts/select_variant.sh (KRI_VARIANT env > .kri-variant.local > gpu default).
# The selector validates the value and rejects typos.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VARIANT="$("$SCRIPT_DIR/scripts/select_variant.sh")"

echo "[kri-local-rag] variant=${VARIANT} (set via 'make use-gpu' / 'make use-cpu' to switch)"

# Ensure a .venv exists and is seeded with pip
uv venv --seed

# Fallback: if pip still missing for any reason, try ensurepip
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  .venv/bin/python -m ensurepip --upgrade || true
fi

# Create or reuse .venv, then sync test group with the selected extra.
# Pass-through args ($@) let callers add flags like --frozen or extra groups.
uv sync --extra "$VARIANT" --group test "$@"

# Quick sanity print
uv run python -V
echo "Env ready. Use: 'uv run <cmd>' or '.venv/bin/<cmd>'."
