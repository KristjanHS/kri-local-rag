#!/usr/bin/env bash
# Wrapper around act-cli to replicate the full GitHub Actions workflow locally.
# This runs both linting and the container-based integration tests.
# Automatically cleans up volumes after completion to prevent accumulation.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

SCRIPT_NAME="ci_act"
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"

log INFO "Running local CI (act) … matching .github/workflows/python-lint-test.yml" | tee -a "$LOG_FILE"
# Explicitly trigger the 'pull_request' job set; pass through user flags
# Capture the exit code from act
set +e
act pull_request --pull=false "$@" 2>&1 | tee -a "$LOG_FILE"
ACT_EXIT_CODE=$?
set -e

# Always cleanup volumes regardless of act success/failure
log INFO "Cleaning up act volumes to prevent accumulation..." | tee -a "$LOG_FILE"
docker volume ls | grep "^local.*act-" | awk '{print $2}' | xargs -r docker volume rm || true

log INFO "Act completed with exit code: $ACT_EXIT_CODE" | tee -a "$LOG_FILE"
exit $ACT_EXIT_CODE
