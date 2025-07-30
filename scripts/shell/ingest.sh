#!/usr/bin/env bash
# Usage: ./scripts/shell/ingest.sh [path-to-pdf-or-directory]
# Runs the PDF ingestion pipeline inside the 'app' container, creating it if necessary.
# If no path is provided, defaults to 'data/' which is mapped to data/ in the project root.

set -e

# Get the project root directory (one level up from scripts/shell/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Change to project root for docker commands
cd "$PROJECT_ROOT"

# Default to data/ (mapped to data/ in project root) if no argument provided
if [ $# -lt 1 ]; then
  DATA_PATH="data/"
else
  # If a relative path is provided, make it relative to project root
  if [[ "$1" != /* ]]; then
    DATA_PATH="$PROJECT_ROOT/$1"
  else
    DATA_PATH="$1"
  fi
fi

docker compose -f docker/docker-compose.yml run --rm app python backend/ingest_pdf.py --data-dir "$DATA_PATH" 