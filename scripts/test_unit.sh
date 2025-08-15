#!/bin/bash
set -euo pipefail

# Convenience wrapper for unit test bundle
# Usage: bash scripts/test_unit.sh

echo "Running unit test bundle..."
.venv/bin/python -m pytest tests/unit -n auto -q
