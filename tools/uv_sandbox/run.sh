#!/usr/bin/env bash
set -euo pipefail

# Ensure uv in PATH for this shell
if ! command -v uv >/dev/null 2>&1; then
  # Try to source user install location from the installer
  if [ -f "$HOME/.local/bin/env" ]; then
    # shellcheck source=/dev/null
    source "$HOME/.local/bin/env"
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found in PATH. Please install uv first (see https://astral.sh/uv)." >&2
  exit 1
fi

export PIP_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"

# Lock, create venv, sync, and validate dependency graph
if [ -f "uv.lock" ]; then
  uv lock --frozen-lockfile
  uv venv --frozen-lockfile
  uv sync --locked --frozen-lockfile
else
  uv lock
  uv venv
  uv sync --locked
fi
uv run python -m pip check
uv tree


