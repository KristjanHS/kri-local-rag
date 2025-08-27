#!/usr/bin/env bash
# Usage: ./scripts/ingest.sh [path-to-pdf-or-directory]
# Runs the PDF ingestion pipeline inside the 'app' container, creating it if necessary.
# If no path is provided, defaults to 'data/' which is mapped to data/ in the project root.

set -Eeuo pipefail

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Setup logging (timestamped file + stable symlink) and traps
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"
log INFO "Starting $SCRIPT_NAME" | tee -a "$LOG_FILE"

# Default to data/ (mapped to data/ in project root) if no argument provided
if [ $# -lt 1 ]; then
  DATA_PATH="$DEFAULT_DATA_PATH"
  REL_PATH="$DATA_PATH"
  log INFO "No data path provided, using default: $DATA_PATH" | tee -a "$LOG_FILE"
else
  # Use the resolve_path function to handle both relative and absolute paths
  DATA_PATH="$(resolve_path "$1")"
  # Convert to a path relative to project root so it maps inside the container (working_dir=/app)
  REL_PATH="$(get_relative_path "$DATA_PATH")"
  log INFO "Using provided data path: $DATA_PATH (container: $REL_PATH)" | tee -a "$LOG_FILE"
fi

log INFO "Starting PDF ingestion with data path: $REL_PATH" | tee -a "$LOG_FILE"
docker compose -f "$DOCKER_COMPOSE_FILE" run --rm "$APP_SERVICE" python -m backend.ingest --data-dir "$REL_PATH" 2>&1 | tee -a "$LOG_FILE"