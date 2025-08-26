#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PY=".venv/bin/python"
COMPOSE_FILE="$REPO_ROOT/docker/docker-compose.yml"
COMPOSE_TEST_FILE="$REPO_ROOT/docker/compose.test.yml"

usage() {
  cat >&2 <<EOF
Usage: $0 <command> [options...]

Test Commands:
  unit                    Run unit tests (fast, no external dependencies)
  integration             Run integration tests (requires test environment)
  e2e                     Run end-to-end tests (full stack, auto-teardown)
  ui                      Run UI tests (Playwright, no coverage)
  all                     Run all test suites in sequence
  
CI Commands:
  fast                    Run fast local checks (ruff + pytest, no Docker)
  ci                      Run full CI simulation (act-based)
  
Environment Commands:
  up                      Start test environment
  down                    Stop test environment  
  logs                    Show test environment logs
  clean                   Clean test environment and cache

Examples:
  $0 unit                 # Run unit tests
  $0 integration          # Run integration tests (requires 'up' first)
  $0 e2e                  # Run e2e tests (auto-manages environment)
  $0 fast                 # Quick local checks
  $0 up && $0 integration # Start env, run integration tests
  $0 all                  # Run all test suites

For pytest options, append after -- :
  $0 unit -- -k test_specific_function
  $0 integration -- --tb=long
EOF
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

command="$1"; shift || true

case "$command" in
  unit)
    echo "Running unit tests..."
    exec "$PY" -m pytest tests/unit -q "$@"
    ;;
    
  integration)
    # Check if test environment is running
    if [[ ! -f .run_id ]]; then
      echo "Error: Test environment not running. Run '$0 up' first." >&2
      exit 1
    fi
    
    RUN_ID=$(cat .run_id)
    echo "Running integration tests in Compose environment (RUN_ID=$RUN_ID)..."
    
    # Run tests inside the app container
    docker compose -f "$COMPOSE_FILE" -f "$COMPOSE_TEST_FILE" -p "$RUN_ID" exec -T app /opt/venv/bin/python3 -m pytest tests/integration -q "$@"
    ;;
    
  e2e)
    echo "Running end-to-end tests..."
    # Bring up full stack, run e2e, then tear down. Honor TEARDOWN_DOCKER/KEEP_DOCKER_UP envs.
    set -x
    docker compose -f "$COMPOSE_FILE" up -d --wait
    set +x
    # Ensure cleanup on exit unless KEEP_DOCKER_UP=1
    cleanup() {
      if [[ -n "${KEEP_DOCKER_UP:-}" && "$KEEP_DOCKER_UP" != "0" && "$KEEP_DOCKER_UP" != "false" ]]; then
        echo "[test.sh] Leaving Docker stack up (KEEP_DOCKER_UP set)."
        return 0
      fi
      echo "[test.sh] Tearing down Docker stack (down, preserving volumes)…"
      docker compose -f "$COMPOSE_FILE" down || true
    }
    trap cleanup EXIT INT TERM
    "$PY" -m pytest tests/e2e -q "$@"
    ;;
    
  ui)
    echo "Running UI tests..."
    # UI suite requires no coverage and Playwright browsers installed
    exec "$PY" -m pytest tests/ui --no-cov -q "$@"
    ;;
    
  all)
    echo "Running all test suites..."
    echo "=== Unit Tests ==="
    "$0" unit "$@"
    echo "=== Integration Tests ==="
    "$0" up
    (trap '"$0" down' EXIT; "$0" integration "$@")
    echo "=== E2E Tests ==="
    "$0" e2e "$@"
    echo "=== UI Tests ==="
    "$0" ui "$@"
    echo "=== All tests completed ==="
    ;;
    
  fast)
    echo "Running fast local checks..."
    source "$SCRIPT_DIR/config.sh"
    SCRIPT_NAME="test_fast"
    LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
    enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
    enable_debug_trace "$LOG_FILE"
    
    need() {
      if ! command -v "$1" >/dev/null 2>&1; then
        if [[ "${CI_STRICT:-}" == "1" ]]; then
          log ERROR "Required tool '$1' not found in PATH" | tee -a "$LOG_FILE"
          exit 1
        else
          log WARN "Optional tool '$1' not found – skipping related step" | tee -a "$LOG_FILE"
          return 1
        fi
      fi
    }
    
    # Ruff – static analysis & formatting (fast)
    if need ruff; then
      log INFO "Running ruff (lint & format check)…" | tee -a "$LOG_FILE"
      ruff check "$REPO_ROOT" | tee -a "$LOG_FILE"
    fi
    
    # Ruff formatting enforcement
    if need ruff; then
      log INFO "Running ruff format --check …" | tee -a "$LOG_FILE"
      ruff format --check "$REPO_ROOT" | tee -a "$LOG_FILE"
    fi
    
    # Pytest – unit & integration tests
    if [[ ! -x "$PY" ]]; then
      log ERROR "$PY does not exist or is not executable. Create the venv first." | tee -a "$LOG_FILE"
      exit 1
    fi
    
    log INFO "Running pytest (fast suite – default addopts) …" | tee -a "$LOG_FILE"
    "$PY" -m pytest -q tests/ | tee -a "$LOG_FILE" || exit $?
    
    log INFO "All local fast checks passed!" | tee -a "$LOG_FILE"
    ;;
    
  ci)
    echo "Running full CI simulation (act)..."
    source "$SCRIPT_DIR/config.sh"
    SCRIPT_NAME="test_ci"
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
    
    # Additional cleanup for any remaining volumes (containers are auto-removed by --rm flag)
    log INFO "Cleaning up any remaining act volumes..." | tee -a "$LOG_FILE"
    docker volume ls | grep "^local.*act-" | awk '{print $2}' | xargs -r docker volume rm || true
    
    log INFO "Act completed with exit code: $ACT_EXIT_CODE" | tee -a "$LOG_FILE"
    exit $ACT_EXIT_CODE
    ;;
    
  up)
    echo "Starting test environment..."
    make test-up
    ;;
    
  down)
    echo "Stopping test environment..."
    make test-down
    ;;
    
  logs)
    echo "Showing test environment logs..."
    make test-logs
    ;;
    
  clean)
    echo "Cleaning test environment and cache..."
    make test-clean
    ;;
    
  *)
    usage
    ;;
esac


