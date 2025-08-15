#!/usr/bin/env bash
set -euo pipefail

echo "--- Setting up Python virtual environment ---"
python -m venv .venv

echo "--- Upgrading pip ---"
.venv/bin/python -m pip install --upgrade pip

echo "--- Installing development requirements ---"
.venv/bin/pip install -r requirements-dev.txt

echo "--- Installing project in editable mode ---"
.venv/bin/pip install -e .

echo "--- Installing linters ---"
# Pinning linter versions for reproducible devcontainer builds
export HADOLINT_VERSION=${HADOLINT_VERSION:-2.12.0}
export ACTIONLINT_VERSION=${ACTIONLINT_VERSION:-1.7.1}
./scripts/install-system-tools.sh

echo "--- Devcontainer setup complete ---"
