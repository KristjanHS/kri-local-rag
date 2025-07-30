#!/bin/bash
#!/bin/bash
# CLI wrapper for the RAG backend - uses APP container

set -e

# Get the project root directory (one level up from scripts/shell/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Check if we're in the project root
if [ ! -f "$PROJECT_ROOT/docker/docker-compose.yml" ]; then
    echo "Error: Please run this script from the project root directory."
    exit 1
fi

# Change to project root for docker commands
cd "$PROJECT_ROOT"

# Start the app container if not running
echo "Starting APP container..."
docker compose -f docker/docker-compose.yml up -d app

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
    docker compose -f docker/docker-compose.yml exec app python backend/qa_loop.py
else
    # Run the provided command in the APP container
    echo "Running command in APP container: $*"
    docker compose -f docker/docker-compose.yml exec app "$@"
fi
