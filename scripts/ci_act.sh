#!/usr/bin/env bash
# Wrapper around act-cli to replicate the GitHub Actions workflow locally.
# Ensures we use the .actrc mapping and stay offline (no image pulls).

set -euo pipefail

# Build (or pull first time) required images ahead of time for offline runs.
# Pass --pull=false to avoid network.
act "${1:-push}" \
    -j lint-and-test \
    --container-architecture linux/amd64 \
    --pull=false
