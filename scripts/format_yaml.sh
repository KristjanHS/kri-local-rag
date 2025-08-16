#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper for yamlfmt.
# Accepts file paths as arguments. If no args, formats common YAML directories.

if [ $# -eq 0 ]; then
  # Default directories to format if no arguments are provided.
  yamlfmt .github/ docker/ .pre-commit-config.yaml Continue_AI_coder/ .gemini/
else
  # Pass through any arguments to yamlfmt.
  yamlfmt "$@"
fi
