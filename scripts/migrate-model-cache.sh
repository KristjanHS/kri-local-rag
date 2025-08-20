#!/bin/bash
# One-time migration script to copy existing models from project model_cache 
# to the Docker volume hf_cache

set -euo pipefail

# Change to project root directory
cd "$(dirname "$0")/.."

echo "=== Model Cache Migration ==="
echo "Migrating models from local model_cache/ to Docker volume hf_cache..."

# Check if model_cache directory exists and has models
if [ ! -d "model_cache" ]; then
    echo "No model_cache directory found. Nothing to migrate."
    exit 0
fi

if [ -z "$(ls -A model_cache 2>/dev/null)" ]; then
    echo "model_cache directory is empty. Nothing to migrate."
    exit 0
fi

echo "Found models in model_cache/:"
ls -la model_cache/

# Start a temporary container with the volume mounted to copy the models
echo "Starting temporary container to copy models..."
docker run --rm \
    -v "$(pwd)/model_cache:/source_cache:ro" \
    -v "kri-local-rag_hf_cache:/dest_cache" \
    alpine:latest \
    sh -c "
        echo 'Copying models from /source_cache to /dest_cache...'
        cp -r /source_cache/* /dest_cache/
        echo 'Migration complete. Contents of /dest_cache:'
        ls -la /dest_cache/
    "

echo "=== Migration Complete ==="
echo "Models have been copied to the hf_cache Docker volume."
echo "Both production and test containers will now use the shared model cache."
