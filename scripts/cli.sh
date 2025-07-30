#!/bin/bash
# CLI wrapper for the RAG backend - uses APP container

set -e

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Start the app container if not running
echo "Starting APP container..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d "$APP_SERVICE"

# Wait for the app container to be ready
echo "Waiting for APP container to be ready..."
sleep 3

# If no arguments provided, start qa_loop.py by default
if [ $# -eq 0 ]; then
    echo "Starting interactive CLI session in APP container..."
    echo "Available commands:"
    echo "  python backend/qa_loop.py          # Interactive RAG CLI (default)"
    echo "  python backend/ingest_pdf.py       # Ingest PDFs. By default, from docs/ directory."
    echo "  python backend/delete_collection.py # Delete all data"
    echo "  bash                               # Start bash shell"
    echo ""
    docker compose -f "$DOCKER_COMPOSE_FILE" exec "$APP_SERVICE" python backend/qa_loop.py
else
    # Run the provided command in the APP container
    echo "Running command in APP container: $*"
    docker compose -f "$DOCKER_COMPOSE_FILE" exec "$APP_SERVICE" "$@"
fi
