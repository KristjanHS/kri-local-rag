#!/usr/bin/env bash
set -euo pipefail

echo "--- Setting up Python virtual environment (uv) ---"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install from https://astral.sh/uv" >&2
  exit 1
fi

# Ensure venv exists and is seeded with pip for any tools that still expect it
uv venv --seed

echo "--- Syncing test dependencies via make uv-sync-test ---"
make uv-sync-test

echo "--- Verifying Python and ruff availability ---"
.venv/bin/python --version
.venv/bin/ruff --version

echo "--- Installing system linters/tools ---"
# Pinning linter versions for reproducible devcontainer builds
export HADOLINT_VERSION=${HADOLINT_VERSION:-2.12.0}
export ACTIONLINT_VERSION=${ACTIONLINT_VERSION:-1.7.1}
./scripts/ci/install-system-tools.sh

echo "--- Development environment setup complete (uv) ---"
