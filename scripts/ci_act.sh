#!/usr/bin/env bash
# Wrapper around act-cli to replicate the full GitHub Actions workflow locally.
# This runs both linting and the container-based integration tests.

set -euo pipefail

echo "🚀 Running full local CI pipeline with act..."

# Explicitly trigger the 'push' event, running all jobs.
# Pass any extra arguments from the command line to act (e.g., -v).
act "push" --pull=false "$@"
