#!/bin/bash
# CLI wrapper for the RAG backend - uses APP container

set -e

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Setup logging
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(get_log_file "$SCRIPT_NAME")
setup_logging "$SCRIPT_NAME"

# Start the app container if not running
log_message "INFO" "Starting APP container"
echo "Starting APP container..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d "$APP_SERVICE" 2>&1 | tee -a "$LOG_FILE"

# Clear Python cache inside the container to ensure latest code is used
log_message "INFO" "Clearing Python bytecode cache (.pyc files) inside APP container"
echo "Clearing Python bytecode cache (.pyc files) inside APP container..."
docker compose -f "$DOCKER_COMPOSE_FILE" exec "$APP_SERVICE" find /app -name '*.pyc' -delete 2>&1 | tee -a "$LOG_FILE"

# Restart the APP container to pick up any code changes
log_message "INFO" "Restarting APP container to apply code changes"
echo "Restarting APP container to apply code changes..."
docker compose -f "$DOCKER_COMPOSE_FILE" restart "$APP_SERVICE" 2>&1 | tee -a "$LOG_FILE"

# Wait for the app container to be ready again
log_message "INFO" "Waiting for APP container to be ready"
echo "Waiting for APP container to be ready..."
sleep 3

# Check for debug flag
DEBUG_MODE=false
if [[ "$1" == "--debug" ]]; then
    DEBUG_MODE=true
    shift  # Remove --debug from arguments
fi

# If no arguments provided, start qa_loop.py by default
if [ $# -eq 0 ]; then
    log_message "INFO" "Starting interactive CLI session in APP container"
    
    if [ "$DEBUG_MODE" = true ]; then
        echo "DEBUG MODE ENABLED - You will see detailed streaming logs"
        echo ""
    fi
    
    echo "Launching Interactive RAG CLI..."
    echo ""
    echo "💡 Other available commands you can run with this script:"
    echo "   ./scripts/cli.sh python backend/ingest_pdf.py       # Ingest PDFs"
    echo "   ./scripts/cli.sh python backend/delete_collection.py # Delete all data"
    echo "   ./scripts/cli.sh bash                               # Start bash shell"
    echo ""
    
    if [ "$DEBUG_MODE" = true ]; then
        docker compose -f "$DOCKER_COMPOSE_FILE" exec -e LOG_LEVEL=DEBUG "$APP_SERVICE" python backend/qa_loop.py 2>&1 | tee -a "$LOG_FILE"
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" exec "$APP_SERVICE" python backend/qa_loop.py 2>&1 | tee -a "$LOG_FILE"
    fi
else
    # Run the provided command in the APP container
    log_message "INFO" "Running command in APP container: $*"
    echo "Running command in APP container: $*"
    docker compose -f "$DOCKER_COMPOSE_FILE" exec "$APP_SERVICE" "$@" 2>&1 | tee -a "$LOG_FILE"
fi
