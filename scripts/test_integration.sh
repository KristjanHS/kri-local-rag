#!/bin/bash
set -euo pipefail

# Convenience wrapper for integration test bundle
# Usage: bash scripts/test_integration.sh

echo "Running integration test bundle..."
.venv/bin/python -m pytest tests/integration -q
