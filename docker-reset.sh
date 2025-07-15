#!/bin/bash
# This script stops and deletes all Docker containers, images, and volumes
# related to the kri-local-rag project for a complete reset.

# Exit immediately if a command exits with a non-zero status.
set -e

# ANSI color codes for printing in red
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Confirmation Prompt ---
echo -e "${RED}WARNING: This script will permanently delete all Docker containers, volumes (including the Weaviate database and Ollama models), and custom images associated with this project.${NC}"
echo -e "${RED}This is a destructive operation and cannot be undone.${NC}"
echo ""
read -p "Are you sure you want to continue? Type 'yes' to proceed: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Cleanup cancelled by user."
    exit 0
fi

echo ""
echo "--- Confirmation received. Proceeding with cleanup... ---"


echo ""
echo "--- Shutting down project containers and removing volumes... ---"
# The --file flag allows this script to be run from the project root.
# --volumes removes the named volumes (weaviate_db, ollama_models).
# --remove-orphans cleans up any containers that are not defined in the compose file.
docker compose --file docker/docker-compose.yml down --volumes --remove-orphans

echo ""
echo "--- Removing project-specific Docker images... ---"
# Find all images with names starting with 'kri-local-rag-' and forcefully remove them.
# The '|| true' ensures that the script doesn't fail if no such images are found.
docker rmi -f $(docker images 'kri-local-rag-*' -q) || true


echo ""
echo "--- Pruning unused Docker resources (build cache, etc.)... ---"
# The -a flag removes all unused images, not just dangling ones.
# The -f flag skips the confirmation prompt.
docker system prune -a -f

echo ""
echo "✅ Docker cleanup complete. You can now start the setup from scratch." 