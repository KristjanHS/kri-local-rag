#!/bin/bash
set -euo pipefail

# Convenience wrapper for e2e test bundle
# Usage: bash scripts/test_e2e.sh

echo "Running e2e test bundle..."

# Ensure the app image is built
bash scripts/build_app_if_missing.sh

.venv/bin/python -m pytest tests/e2e -q
