#!/usr/bin/env bash
# scripts/local_fast_checks.sh – lightweight, offline developer checks
#
# Purpose
# - Fast feedback loop (no Docker, no act): Ruff + pytest via local .venv
# - Complements act/GitHub CI by being dependency-light and offline-friendly
# - Mirrors CI’s default pytest addopts (excludes environment/e2e/slow)
#
# When to use which
# - Use this script for quick local iteration and offline work
# - Use scripts/ci_act.sh (act) to emulate GitHub Actions (Docker-based)
# - Git hook .git/hooks/pre-push runs act for PR checks automatically
#
# USAGE
#   ./scripts/local_fast_checks.sh              # run all default checks
#   CI_STRICT=1 ./scripts/local_fast_checks.sh  # fail instead of warn on missing tools
#
# Prereq: the project-level .venv exists and deps installed:
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

_green "Running pytest (fast suite – default addopts) …"
"$PY" -m pytest -q tests/

_green "All local fast checks passed!"
