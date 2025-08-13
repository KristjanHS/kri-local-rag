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

# Detect if 'act' is available; we'll use native tools where possible and only run act-based steps when available
if command -v act >/dev/null 2>&1; then
  ACT_AVAILABLE=1
else
  ACT_AVAILABLE=0
  log WARN "'act' not found. Will run native checks only (ruff/pyright); skipping act-based steps. Install: https://github.com/nektos/act" | tee -a "$LOG_FILE"
fi

# Honor optional guard to skip local security scans (CodeQL/Semgrep)
# Default to skipping heavy security scans locally for faster pushes.
# Opt-in by setting SKIP_LOCAL_SEC_SCANS=0 when you want to run them.
SKIP_LOCAL_SEC_SCANS=${SKIP_LOCAL_SEC_SCANS:-1}
if [[ "$SKIP_LOCAL_SEC_SCANS" == "1" ]]; then
  log INFO "SKIP_LOCAL_SEC_SCANS=1 — security scans will be skipped" | tee -a "$LOG_FILE"
fi

# Optional local skip toggles (developer ergonomics)
SKIP_LINT=${SKIP_LINT:-0}
SKIP_PYRIGHT=${SKIP_PYRIGHT:-0}
SKIP_TESTS=${SKIP_TESTS:-0}
if [[ "$SKIP_LINT" == "1" ]]; then
  log INFO "SKIP_LINT=1 — lint checks will be skipped" | tee -a "$LOG_FILE"
fi
if [[ "$SKIP_PYRIGHT" == "1" ]]; then
  log INFO "SKIP_PYRIGHT=1 — type checks will be skipped" | tee -a "$LOG_FILE"
fi
if [[ "$SKIP_TESTS" == "1" ]]; then
  log INFO "SKIP_TESTS=1 — tests will be skipped" | tee -a "$LOG_FILE"
fi

# Run ruff (format check + lint) natively from the project venv
if [[ "$SKIP_LINT" != "1" ]]; then
  if [[ -x ".venv/bin/ruff" ]]; then
    log INFO "Running ruff format --check …" | tee -a "$LOG_FILE"
    .venv/bin/ruff format --check . 2>&1 | tee -a "$LOG_FILE"
    log INFO "Running ruff check …" | tee -a "$LOG_FILE"
    .venv/bin/ruff check . 2>&1 | tee -a "$LOG_FILE"
  else
    log WARN "'.venv/bin/ruff' not found. Skipping ruff checks. Ensure dev deps are installed: 'pip install -e .[test,docs,cli]'" | tee -a "$LOG_FILE"
  fi
else
  log INFO "Skipping ruff due to SKIP_LINT=1" | tee -a "$LOG_FILE"
fi

# Run pyright (type checking) natively from the project venv
if [[ "$SKIP_PYRIGHT" != "1" ]]; then
  if [[ -x ".venv/bin/pyright" ]]; then
    log INFO "Running pyright (native) …" | tee -a "$LOG_FILE"
    .venv/bin/pyright 2>&1 | tee -a "$LOG_FILE"
  else
    log WARN "'.venv/bin/pyright' not found. Skipping type checks. Install pyright in the venv (e.g., add to dev deps)." | tee -a "$LOG_FILE"
  fi
else
  log INFO "Skipping pyright due to SKIP_PYRIGHT=1" | tee -a "$LOG_FILE"
fi

# Run fast tests (keep via act for parity when available)
if [[ "$SKIP_TESTS" == "1" ]]; then
  log INFO "Skipping tests due to SKIP_TESTS=1" | tee -a "$LOG_FILE"
else
  if [[ "$ACT_AVAILABLE" == "1" ]]; then
    log INFO "Running fast_tests via act (pull_request) …" | tee -a "$LOG_FILE"
    act pull_request -j fast_tests --pull=false --reuse --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE"
  else
    # Native fast path for quick feedback when act isn't available
    if [[ -x ".venv/bin/python" ]]; then
      log INFO "Running native fast tests: pytest --test-fast --maxfail=1 -q …" | tee -a "$LOG_FILE"
      .venv/bin/python -m pytest --test-fast --maxfail=1 -q 2>&1 | tee -a "$LOG_FILE"
    else
      log WARN "'.venv/bin/python' not found; cannot run native fast tests." | tee -a "$LOG_FILE"
    fi
  fi
fi

# Run local Semgrep via pipx (isolated) unless skipped
if [[ "$SKIP_LOCAL_SEC_SCANS" != "1" ]]; then
  if [[ "$ACT_AVAILABLE" == "1" ]]; then
    log INFO "Running Semgrep (local workflow) via act …" | tee -a "$LOG_FILE"
    act workflow_dispatch -W .github/workflows/semgrep_local.yml --pull=false --reuse --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE" || true
  else
    log INFO "Running Semgrep (local) via pipx …" | tee -a "$LOG_FILE"
    bash "$SCRIPT_DIR/semgrep_local.sh" 2>&1 | tee -a "$LOG_FILE" || true
  fi
else
  log INFO "Skipping Semgrep due to SKIP_LOCAL_SEC_SCANS=1" | tee -a "$LOG_FILE"
fi

# Optional: run CodeQL locally (informational)
if [[ "$SKIP_LOCAL_SEC_SCANS" != "1" ]]; then
  if [[ "$ACT_AVAILABLE" == "1" ]]; then
    log INFO "Running CodeQL (informational) via act …" | tee -a "$LOG_FILE"
    act pull_request -W .github/workflows/codeql.yml --pull=false --reuse --log-prefix-job-id 2>&1 | tee -a "$LOG_FILE" || true
  else
    log INFO "Skipping CodeQL (act not available)." | tee -a "$LOG_FILE"
  fi
else
  log INFO "Skipping CodeQL due to SKIP_LOCAL_SEC_SCANS=1" | tee -a "$LOG_FILE"
fi

log INFO "Pre-push checks complete" | tee -a "$LOG_FILE"
exit 0


