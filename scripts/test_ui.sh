#!/bin/bash
set -euo pipefail

# Convenience wrapper for UI test bundle
# Usage: bash scripts/test_ui.sh

echo "Running UI test bundle..."
.venv/bin/python -m pytest tests/ui --no-cov -q
