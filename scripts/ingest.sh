#!/usr/bin/env bash
# Usage: ./scripts/ingest.sh [path-to-pdf-or-directory]
# Runs the PDF ingestion pipeline inside the 'app' container, creating it if necessary.
# If no path is provided, defaults to 'data/' which is mapped to data/ in the project root.

set -e

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Default to data/ (mapped to data/ in project root) if no argument provided
if [ $# -lt 1 ]; then
  DATA_PATH="$DEFAULT_DATA_PATH"
else
  # Use the resolve_path function to handle both relative and absolute paths
  DATA_PATH="$(resolve_path "$1")"
fi

docker compose -f "$DOCKER_COMPOSE_FILE" run --rm "$APP_SERVICE" python backend/ingest_pdf.py --data-dir "$DATA_PATH" 