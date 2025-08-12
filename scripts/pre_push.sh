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

# Provide both lowercase and uppercase names for compatibility with helper scripts
script_name="pre-push"
SCRIPT_NAME="pre-push"

# Try to load shared helpers if present; otherwise define minimal no-op/logging stubs
if [[ -f "$SCRIPT_DIR/config.sh" ]]; then
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/config.sh"
else
  mkdir -p logs
  log() {
    local level="$1"; shift || true
    local msg="$*"
    local ts
    ts="$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "$ts [$level] $msg"
  }
  init_script_logging() {
    local name="$1"
    local f="logs/${name}.log"
    : >"$f"
    echo "$f"
  }
  enable_error_trap() { :; }
  enable_debug_trace() { :; }
fi

LOG_FILE=$(init_script_logging "$script_name")
enable_error_trap "$LOG_FILE" "$script_name"
enable_debug_trace "$LOG_FILE"

log INFO "Starting pre-push checks" | tee -a "$LOG_FILE"

if ! command -v act >/dev/null 2>&1; then
  log WARN "'act' not found. Skipping local CI checks. Install: https://github.com/nektos/act" | tee -a "$LOG_FILE"
  exit 0
fi

# Honor optional guard to skip local security scans (CodeQL/Semgrep)
# Default to skipping heavy security scans locally for faster pushes.
# Opt-in by setting SKIP_LOCAL_SEC_SCANS=0 when you want to run them.
SKIP_LOCAL_SEC_SCANS=${SKIP_LOCAL_SEC_SCANS:-1}
if [[ "$SKIP_LOCAL_SEC_SCANS" == "1" ]]; then
  log INFO "SKIP_LOCAL_SEC_SCANS=1 — security scans will be skipped" | tee -a "$LOG_FILE"
fi

# Run pyright (type checking). This job is configured to run under workflow_dispatch only.
log INFO "Running pyright via act (workflow_dispatch) …" | tee -a "$LOG_FILE"
act workflow_dispatch -j pyright --pull=false --reuse --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE"

# Run lint job
log INFO "Running lint via act (pull_request) …" | tee -a "$LOG_FILE"
act pull_request -j lint --pull=false --reuse --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE"

# Run fast tests
log INFO "Running fast_tests via act (pull_request) …" | tee -a "$LOG_FILE"
act pull_request -j fast_tests --pull=false --reuse --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE"

# Optional: run CodeQL locally (informational)
if [[ "$SKIP_LOCAL_SEC_SCANS" != "1" ]]; then
  log INFO "Running CodeQL (informational) via act …" | tee -a "$LOG_FILE"
  act pull_request -W .github/workflows/codeql.yml --pull=false --reuse --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE" || true
else
  log INFO "Skipping CodeQL due to SKIP_LOCAL_SEC_SCANS=1" | tee -a "$LOG_FILE"
fi

log INFO "Pre-push checks complete" | tee -a "$LOG_FILE"
exit 0


