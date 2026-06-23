#!/usr/bin/env bash
set -euo pipefail

echo "--- Setting up Python virtual environment (uv) ---"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install from https://astral.sh/uv" >&2
  exit 1
fi

# Seed the venv and sync dependencies. Default torch is the PyPI/GPU wheel; pass
# `--extra cpu` (or run `./run_uv.sh --extra cpu`) on CPU-only boxes. run_uv.sh
# handles venv creation + sync.
echo "--- Syncing dependencies via run_uv.sh ---"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
"$REPO_ROOT/run_uv.sh"

echo "--- Verifying Python and ruff availability ---"
.venv/bin/python --version
.venv/bin/ruff --version

echo "--- Installing system linters/tools ---"
# Pinning linter versions for reproducible devcontainer builds
export HADOLINT_VERSION=${HADOLINT_VERSION:-2.12.0}
export ACTIONLINT_VERSION=${ACTIONLINT_VERSION:-1.7.1}
./scripts/ci/install-system-tools.sh

echo "--- Development environment setup complete (uv) ---"
