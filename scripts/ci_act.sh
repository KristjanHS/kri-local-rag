#!/usr/bin/env bash
# Wrapper around act-cli to replicate the full GitHub Actions workflow locally.
# This runs both linting and the container-based integration tests.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

SCRIPT_NAME="ci_act"
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"

log INFO "Running local CI (act) … matching .github/workflows/python-lint-test.yml" | tee -a "$LOG_FILE"

# Explicitly trigger the 'pull_request' job set; pass through user flags
act pull_request --pull=false "$@" 2>&1 | tee -a "$LOG_FILE"
