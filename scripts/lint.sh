#!/usr/bin/env bash
# scripts/lint.sh - Runs Ruff to automatically reformat and fix lint errors.
set -euo pipefail

echo "🔍 Running Ruff to fix and reformat files..."

# 1. Fix all fixable linting errors (like removing unused imports)
ruff check . --fix

# 2. Reformat all files according to the rules in pyproject.toml
ruff format .

echo "✅ Ruff auto-fixing and formatting complete."
