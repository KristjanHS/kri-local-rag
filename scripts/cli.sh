#!/usr/bin/env bash
#
# QA loop CLI entrypoint: Starts the interactive console.
# Pass any arguments to the python script.

set -euo pipefail

# Get the directory of this script to find the project root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# Use the project virtual environment explicitly (repo rule)
VENV_PATH="${PROJECT_ROOT}/.venv"
VENV_PY="${VENV_PATH}/bin/python"
if [ ! -x "${VENV_PY}" ]; then
    echo "Error: ${VENV_PY} not found. Create the venv and install deps first." >&2
    echo "Hint: make dev-setup or make uv-sync-test" >&2
    exit 1
fi

# Ensure text-only Transformers import path in CPU environments
export TRANSFORMERS_NO_TORCHVISION=${TRANSFORMERS_NO_TORCHVISION:-1}

# Run the QA loop from the project root with the venv Python.
exec "${VENV_PY}" -m backend.qa_loop "$@"
