#!/usr/bin/env bash
#
# QA loop CLI entrypoint: Starts the interactive console.
# Pass any arguments to the python script.

set -euo pipefail

# Get the directory of this script to find the project root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# Activate the virtual environment if it exists
VENV_PATH="${PROJECT_ROOT}/.venv"
if [ -f "${VENV_PATH}/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "${VENV_PATH}/bin/activate"
fi

# Ensure text-only Transformers import path in CPU environments
export TRANSFORMERS_NO_TORCHVISION=${TRANSFORMERS_NO_TORCHVISION:-1}

# Run the QA loop from the project root to ensure correct module resolution.
# Pass all script arguments ($@) to the python process.
exec python -m backend.qa_loop "$@"
