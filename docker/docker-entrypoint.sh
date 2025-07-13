#! /bin/sh
# docker-entrypoint.sh – wraps original container entrypoint but first
# exports HF_HUB_TOKEN from a Docker secret (if present) so that
# huggingface_hub can authenticate without baking the token into the image.

# Exit immediately if a command exits with a non-zero status.
set -e

# If the secret mount exists, read it and export
if [ -f "/run/secrets/hf_hub_token" ]; then
  export HF_HUB_TOKEN="$(cat /run/secrets/hf_hub_token)"
  echo "HF_HUB_TOKEN exported from secret."
fi

echo "Attempting to execute original command: $@"
# Execute the original command of the base image, which is passed as arguments ($@)
# Redirect stderr to stdout to ensure all output is captured.
exec "$@" 2>&1