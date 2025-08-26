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

# Avoid interference from the project's root venv
unset VIRTUAL_ENV || true

# No global extra index; indexes are declared in pyproject via [tool.uv.index]

# Lock, create venv, sync, and validate dependency graph
if [ -f "uv.lock" ]; then
  uv lock --check
  uv venv --allow-existing
  uv sync --frozen
else
  uv lock
  uv venv --allow-existing
  uv sync
fi
uv pip check
uv tree


