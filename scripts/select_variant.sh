#!/usr/bin/env bash
# Emit the active uv extras variant ("cpu" or "gpu") for this checkout.
#
# Precedence: $KRI_VARIANT env override > <repo>/.kri-variant.local (gitignored)
# > default "gpu". GPU is the default for local/bare-metal dev; CI/act set
# KRI_VARIANT=cpu. Anything other than "cpu" or "gpu" is rejected with a clear
# error so a typo doesn't silently fall back to the default.
#
# Wrappers (run_uv.sh, Makefile targets) call this and pass `--extra ${variant}`
# to `uv sync`. See docs/plans/2026-06-23-gpu-cpu-torch-extras.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VARIANT_FILE="$REPO_ROOT/.kri-variant.local"

if [ -n "${KRI_VARIANT:-}" ]; then
    VARIANT="$(printf '%s' "$KRI_VARIANT" | tr -d '[:space:]')"
elif [ -f "$VARIANT_FILE" ]; then
    VARIANT="$(tr -d '[:space:]' < "$VARIANT_FILE")"
else
    VARIANT="gpu"
fi

case "$VARIANT" in
    cpu|gpu)
        printf '%s\n' "$VARIANT"
        ;;
    "")
        printf '%s\n' "gpu"
        ;;
    *)
        printf "unknown variant '%s' (KRI_VARIANT or .kri-variant.local) -- expected 'cpu' or 'gpu'\n" "$VARIANT" >&2
        exit 1
        ;;
esac
