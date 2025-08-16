#!/usr/bin/env bash
set -euo pipefail

# Detect if we're running as root (devcontainer) or need sudo (host)
if [ "$(id -u)" -eq 0 ]; then
    SUDO_CMD=""
else
    SUDO_CMD="sudo"
fi

# Debian Bullseye base (your image) — install yamllint via apt.
$SUDO_CMD apt-get update && $SUDO_CMD DEBIAN_FRONTEND=noninteractive apt-get install -y \
  curl jq ca-certificates tar xz-utils python3 python3-pip yamllint file


# --- hadolint (static binary, arch-aware) ---
arch="$(uname -m)"
case "$arch" in
  x86_64)  HL_ARCH="x86_64" ;;
  aarch64|arm64) HL_ARCH="arm64" ;;
  *) echo "Unsupported arch: $arch" && exit 1 ;;
esac

# Optional pin (e.g., HADOLINT_VERSION=2.12.0). Empty => latest.
: "${HADOLINT_VERSION:=}"

# Build the download URL WITHOUT using the GitHub API to avoid 403s.
if [[ -z "${HADOLINT_VERSION}" ]]; then
  HL_URL="https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-${HL_ARCH}"
else
  HL_URL="https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-${HL_ARCH}"
fi

# Replace any old/corrupt binary, download fresh, make executable, and validate
$SUDO_CMD rm -f /usr/local/bin/hadolint
$SUDO_CMD curl -fLso /usr/local/bin/hadolint "${HL_URL}"
$SUDO_CMD chmod +x /usr/local/bin/hadolint
if ! file /usr/local/bin/hadolint | grep -q 'ELF'; then
  echo "Downloaded hadolint is not a valid ELF. URL: ${HL_URL}" >&2
  exit 1
fi

# actionlint (system-wide install into /usr/local/bin)
# Uses official download script with positional args: <version> <install-dir>.
: "${ACTIONLINT_VERSION:=latest}"

# Download and install actionlint system-wide (Codespaces-compatible: avoid process substitution).
TMP_SCRIPT="$(mktemp)"
trap 'rm -f "$TMP_SCRIPT"' EXIT
curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash -o "$TMP_SCRIPT"
$SUDO_CMD bash "$TMP_SCRIPT" "${ACTIONLINT_VERSION}" "/usr/local/bin"

# pyright is installed via pip from requirements-dev.txt into the project's .venv.
# This ensures it's version-pinned and isolated. No system-wide install needed.

# Show versions for a quick sanity check.
echo "Installed versions:"
# Only print the first line of actionlint -version to avoid duplicate details
echo -n "actionlint: " && actionlint -version | head -n 1
echo -n "yamllint: " && yamllint --version
echo -n "hadolint: " && hadolint --version
echo -n "pyright: " && (
  if [ -f ".venv/bin/pyright" ]; then
    .venv/bin/pyright --version 2>/dev/null
  else
    echo "not installed (run pip install -r requirements-dev.txt)"
  fi
)
