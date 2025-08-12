#!/usr/bin/env bash
# Git pre-push hook (template) for running local CI with act
# - Skips gracefully if `act` is not installed
# - Supports skipping security scans locally via SKIP_LOCAL_SEC_SCANS=1

set -Eeuo pipefail

# Resolve script directory, following symlinks (works when called via .git/hooks)
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
source "$SCRIPT_DIR/config.sh"

SCRIPT_NAME="pre-push"
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"

log INFO "Starting pre-push checks" | tee -a "$LOG_FILE"

if ! command -v act >/dev/null 2>&1; then
  log WARN "'act' not found. Skipping local CI checks. Install: https://github.com/nektos/act" | tee -a "$LOG_FILE"
  exit 0
fi

# Honor optional guard to skip local security scans (CodeQL/Semgrep)
SKIP_LOCAL_SEC_SCANS=${SKIP_LOCAL_SEC_SCANS:-0}
if [[ "$SKIP_LOCAL_SEC_SCANS" == "1" ]]; then
  log INFO "SKIP_LOCAL_SEC_SCANS=1 — security scans will be skipped" | tee -a "$LOG_FILE"
fi

# Run pyright (type checking). This job is configured to run under workflow_dispatch only.
log INFO "Running pyright via act (workflow_dispatch) …" | tee -a "$LOG_FILE"
act workflow_dispatch -j pyright --pull=false --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE"

# Run lint job
log INFO "Running lint via act (pull_request) …" | tee -a "$LOG_FILE"
act pull_request -j lint --pull=false --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE"

# Run fast tests
log INFO "Running fast_tests via act (pull_request) …" | tee -a "$LOG_FILE"
act pull_request -j fast_tests --pull=false --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE"

# Optional: run CodeQL locally (informational)
if [[ "$SKIP_LOCAL_SEC_SCANS" != "1" ]]; then
  log INFO "Running CodeQL (informational) via act …" | tee -a "$LOG_FILE"
  act pull_request -W .github/workflows/codeql.yml --pull=false --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE" || true
else
  log INFO "Skipping CodeQL due to SKIP_LOCAL_SEC_SCANS=1" | tee -a "$LOG_FILE"
fi

log INFO "Pre-push checks complete" | tee -a "$LOG_FILE"
exit 0


