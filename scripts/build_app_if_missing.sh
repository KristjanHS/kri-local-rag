#!/bin/bash
# Build the app image if it is missing.

set -Eeuo pipefail

# Source centralized config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

IMAGE_NAME="kri-local-rag-app:latest"

# Check if the image exists
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    log INFO "Image '$IMAGE_NAME' not found. Building..."
    "$SCRIPT_DIR/build_app.sh"
else
    log INFO "Image '$IMAGE_NAME' already exists. Skipping build."
fi
