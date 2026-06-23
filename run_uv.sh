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

# Resolve the per-machine uv extras variant (cpu | gpu) via
# scripts/select_variant.sh (KRI_VARIANT env > .kri-variant.local > gpu default).
# The selector validates the value and rejects typos.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VARIANT="$("$SCRIPT_DIR/scripts/select_variant.sh")"

echo "[kri-local-rag] variant=${VARIANT} (set via 'make use-gpu' / 'make use-cpu' to switch)"

# Create the venv if missing; recreate it clean when the requested variant
# differs from the one last synced (recorded in .venv/.kri-variant). Guarded
# rather than an unconditional `uv venv --seed` for two reasons:
#   1. `uv venv --seed` exits non-zero on an existing venv (it wants --clear);
#      under `set -e` that aborts this script on every re-run once `.venv` exists.
#   2. Incrementally swapping CUDA wheel families (no-extra/cpu torch pulls
#      nvidia-*-cu13; the gpu extra pulls nvidia-*-cu12) corrupts the shared
#      PEP-420 `nvidia/` namespace dir — uv drops nvidia/cusparselt/ on uninstall
#      but skips re-unpacking the replacement, so torch can no longer load
#      libcusparseLt.so.0. A clean venv is the only reliable family swap
#      (`uv sync --reinstall` does NOT repair an already-corrupted tree).
VARIANT_MARKER=".venv/.kri-variant"
LAST_VARIANT="$([ -f "$VARIANT_MARKER" ] && cat "$VARIANT_MARKER" || true)"
if [ ! -d .venv ]; then
  uv venv --seed
elif [ "$LAST_VARIANT" != "$VARIANT" ]; then
  echo "[kri-local-rag] variant changed (${LAST_VARIANT:-none} -> ${VARIANT}); recreating .venv clean"
  uv venv --seed --clear
fi

# Fallback: if pip still missing for any reason, try ensurepip
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  .venv/bin/python -m ensurepip --upgrade || true
fi

# Sync the project + test group with the selected extra. Pass-through args ($@)
# let callers add flags like --frozen or extra groups. Record the synced variant
# so a later switch triggers the clean recreate above.
uv sync --extra "$VARIANT" --group test "$@"
printf '%s\n' "$VARIANT" > "$VARIANT_MARKER"

# Quick sanity print. Invoke the venv interpreter directly — do NOT use
# `uv run` here: cpu/gpu are conflicting extras (never in uv's default set), so
# `uv run` would re-sync the env WITHOUT `--extra "$VARIANT"` and silently revert
# the variant torch we just installed above to the no-extra PyPI default wheel.
.venv/bin/python -V
echo "Env ready. Use: '.venv/bin/<cmd>' (a bare 'uv run <cmd>' re-syncs to the no-extra torch — pass 'uv run --no-sync' to keep the ${VARIANT} variant)."
