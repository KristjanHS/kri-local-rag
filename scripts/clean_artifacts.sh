#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

SCRIPT_NAME="clean_artifacts"
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"

log INFO "Cleaning test reports and old logs…" | tee -a "$LOG_FILE"

# Ensure directories exist
mkdir -p "reports/logs" "$LOGS_DIR"

# 1) Clear test artifacts (safe to regenerate on next pytest run)
find "reports" -mindepth 1 -maxdepth 1 -type f -print -delete 2>&1 | tee -a "$LOG_FILE" || true
find "reports/logs" -type f -print -delete 2>&1 | tee -a "$LOG_FILE" || true

# 2) Prune old script/runtime logs (keep last 7 days)
find "$LOGS_DIR" -type f -name '*.log' -mtime +7 -print -delete 2>&1 | tee -a "$LOG_FILE" || true

log INFO "Done." | tee -a "$LOG_FILE"

