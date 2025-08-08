#!/usr/bin/env bash
# Wrapper around act-cli to replicate the full GitHub Actions workflow locally.
# This runs both linting and the container-based integration tests.

set -euo pipefail

echo "🚀 Running local CI (act) … matching .github/workflows/python-lint-test.yml"

# Explicitly trigger the 'push' event, running all jobs.
# Pass any extra arguments from the command line to act (e.g., -v).
# Tip:
# - The pre-push Git hook runs 'act pull_request -j lint_and_fast_tests'.
# - Use 'act pull_request' locally to reproduce the same job selection.
act pull_request --pull=false "$@"
