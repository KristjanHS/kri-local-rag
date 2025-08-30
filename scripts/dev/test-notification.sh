#!/usr/bin/env bash
# Simple test notification script
# Provides terminal notifications, colored output, and logging

set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

# shellcheck source=scripts/common.sh
source "$ROOT_DIR/scripts/common.sh"

script_name="test-notification"
LOG_FILE=$(init_script_logging "$script_name")
enable_error_trap "$LOG_FILE" "$script_name"

# Configuration
TEST_TYPE=${1:-integration}
NOTIFY_ON_SUCCESS=${NOTIFY_ON_SUCCESS:-true}
NOTIFY_ON_FAILURE=${NOTIFY_ON_FAILURE:-true}

log INFO "Running $TEST_TYPE tests..."

# Check if virtual environment exists
if [[ ! -x ".venv/bin/python" ]]; then
    log ERROR ".venv/bin/python not found"
    echo -e "\033[31m✗ Test setup failed: Missing .venv/bin/python\033[0m"
    exit 1
fi

# Determine test command based on type
case "$TEST_TYPE" in
    "integration")
        TEST_CMD=(.venv/bin/python -m pytest tests/integration -q --junitxml=reports/junit_integration.xml)
        TEST_NAME="Integration Tests"
        ;;
    "unit")
        TEST_CMD=(.venv/bin/python -m pytest tests/unit -q --junitxml=reports/junit_unit.xml)
        TEST_NAME="Unit Tests"
        ;;
    "e2e")
        TEST_CMD=(.venv/bin/python -m pytest tests/e2e -q --junitxml=reports/junit_e2e.xml)
        TEST_NAME="E2E Tests"
        ;;
    "all")
        TEST_CMD=(.venv/bin/python -m pytest tests/ -q --junitxml=reports/junit_all.xml)
        TEST_NAME="All Tests"
        ;;
    *)
        log ERROR "Unknown test type: $TEST_TYPE"
        log INFO "Supported types: integration, unit, e2e, all"
        exit 1
        ;;
esac

# Create reports directory
mkdir -p reports

# Run tests with timing
START_TIME=$(date +%s)
log INFO "Running: ${TEST_CMD[*]}"

set -o pipefail
"${TEST_CMD[@]}" 2>&1 | tee -a "$LOG_FILE"
TEST_RC=${PIPESTATUS[0]:-1}
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Format duration
if [[ $DURATION -lt 60 ]]; then
    DURATION_STR="${DURATION}s"
elif [[ $DURATION -lt 3600 ]]; then
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))
    DURATION_STR="${MINUTES}m ${SECONDS}s"
else
    HOURS=$((DURATION / 3600))
    MINUTES=$(((DURATION % 3600) / 60))
    DURATION_STR="${HOURS}h ${MINUTES}m"
fi

if [[ $TEST_RC -eq 0 ]]; then
    log INFO "$TEST_NAME passed in $DURATION_STR ✓"
    echo -e "\033[32m✓ $TEST_NAME passed in $DURATION_STR\033[0m"
else
    log ERROR "$TEST_NAME failed (exit $TEST_RC) after $DURATION_STR"
    echo -e "\a\033[31m✗ $TEST_NAME failed (exit $TEST_RC) after $DURATION_STR\033[0m"
    echo -e "\033[33mCheck the logs above and fix the failing tests.\033[0m"
    echo -e "\033[33mLog file: $LOG_FILE\033[0m"
fi

exit "$TEST_RC"
