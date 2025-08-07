#!/usr/bin/env bash
# scripts/ci_local.sh – quick offline CI loop for developers
#
# This script reproduces the most important parts of the GitHub CI pipeline
# (lint & tests) but runs entirely against the already-created local virtual
# environment. It is intentionally dependency-free (no docker, no network) so
# that you can iterate rapidly even when offline.
#
# USAGE
#   ./scripts/ci_local.sh          # run all default checks
#   CI_STRICT=1 ./scripts/ci_local.sh   # fail instead of warn on missing tools
#
# The script assumes the project-level .venv already exists and that all
# dependencies are installed – e.g.:
#   python -m venv .venv
#   .venv/bin/pip install -r requirements.txt
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT_DIR/.venv/bin/python"

_red()   { printf "\e[31m%s\e[0m\n" "$*"; }
_green() { printf "\e[32m%s\e[0m\n" "$*"; }
_yellow(){ printf "\e[33m%s\e[0m\n" "$*"; }

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    if [[ "${CI_STRICT:-}" == "1" ]]; then
      _red "ERROR: required tool '$1' not found in PATH" && exit 1
    else
      _yellow "WARN : optional tool '$1' not found – skipping related step" && return 1
    fi
  fi
}

# ---------------------------------------------------------------------------
# 1. Ruff – static analysis & formatting (fast)
# ---------------------------------------------------------------------------
if need ruff; then
  _green "Running ruff (lint & format check)…"
  ruff check "$ROOT_DIR"
  # Ruff can also auto-fix, but CI should only verify
fi

# ---------------------------------------------------------------------------
# 2. Ruff formatting enforcement
# ---------------------------------------------------------------------------
if need ruff; then
  _green "Running ruff format --check …"
  ruff format --check "$ROOT_DIR"
fi

# ---------------------------------------------------------------------------
# 3. Pytest – unit & integration tests
# ---------------------------------------------------------------------------
if [[ ! -x "$PY" ]]; then
  _red "ERROR: $PY does not exist or is not executable. Create the venv first." && exit 1
fi

_green "Running pytest …"
"$PY" -m pytest -q tests/

_green "All checks passed!"
