#!/bin/bash
# This script stops and deletes all Docker containers, images, and volumes
# related to the kri-local-rag project for a complete reset.

# Exit immediately if a command exits with a non-zero status.
set -e

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Setup logging
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(get_log_file "$SCRIPT_NAME")
setup_logging "$SCRIPT_NAME"

# ANSI color codes for printing in red
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Confirmation Prompt ---
log_message "INFO" "Starting Docker reset script"
echo -e "${RED}WARNING: This script will permanently delete all Docker containers, volumes (including the Weaviate database and Ollama models), and custom images associated with this project.${NC}"
echo -e "${RED}This is a destructive operation and cannot be undone.${NC}"
echo ""
read -p "Are you sure you want to continue? Type 'yes' to proceed: " confirmation

if [ "$confirmation" != "yes" ]; then
    log_message "INFO" "Cleanup cancelled by user"
    echo "Cleanup cancelled by user."
    exit 0
fi

log_message "INFO" "Confirmation received, proceeding with cleanup"
echo ""
echo "--- Confirmation received. Proceeding with cleanup... ---"

echo ""
log_message "INFO" "Shutting down project containers and removing volumes"
echo "--- Shutting down project containers and removing volumes... ---"

# The --file flag allows this script to be run from the project root.
# --volumes removes the named volumes (weaviate_db, ollama_models).
# --remove-orphans cleans up any containers that are not defined in the compose file.
docker compose --file "$DOCKER_COMPOSE_FILE" down --volumes --remove-orphans 2>&1 | tee -a "$LOG_FILE"

echo ""
log_message "INFO" "Removing project-specific Docker images"
echo "--- Removing project-specific Docker images... ---"
# Find all images with names starting with 'kri-local-rag-' and forcefully remove them.
# Check if any images exist before attempting to remove them.
PROJECT_IMAGES=$(docker images 'kri-local-rag-*' -q)
if [ -n "$PROJECT_IMAGES" ]; then
    docker rmi -f $PROJECT_IMAGES 2>&1 | tee -a "$LOG_FILE" || true
else
    log_message "INFO" "No project-specific images found to remove"
    echo "No project-specific images found to remove."
fi

echo ""
log_message "INFO" "Pruning unused Docker resources"
echo "--- Pruning unused Docker resources (build cache, etc.)... ---"
# The -a flag removes all unused images, not just dangling ones.
# The -f flag skips the confirmation prompt.
docker system prune -a -f 2>&1 | tee -a "$LOG_FILE"

echo ""
log_message "INFO" "Docker cleanup complete"
echo "✅ Docker cleanup complete. You can now start the setup from scratch." 