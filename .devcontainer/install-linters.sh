#!/usr/bin/env bash
set -euo pipefail

# Debian Bullseye base (your image) — install yamllint via apt.
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
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
sudo rm -f /usr/local/bin/hadolint
sudo curl -fLso /usr/local/bin/hadolint "${HL_URL}"
sudo chmod +x /usr/local/bin/hadolint
if ! file /usr/local/bin/hadolint | grep -q 'ELF'; then
  echo "Downloaded hadolint is not a valid ELF. URL: ${HL_URL}" >&2
  exit 1
fi

# actionlint (user-scope install into ~/.local/bin)
# Uses official download script with positional args: <version> <install-dir>.
: "${ACTIONLINT_VERSION:=latest}"

# Ensure user bin dir exists and is on PATH for future shells.
mkdir -p "${HOME}/.local/bin"
if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "${HOME}/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${HOME}/.bashrc"
fi
# Also update PATH for this current shell so the version check works.
export PATH="$HOME/.local/bin:$PATH"

# Download and install actionlint to user scope.
bash <(curl -fsSL \
  https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash) \
  "${ACTIONLINT_VERSION}" "${HOME}/.local/bin"

# Show versions for a quick sanity check.
echo "Installed versions:"
actionlint -version
yamllint --version
hadolint --version