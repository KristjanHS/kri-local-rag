#!/usr/bin/env bash
set -euo pipefail

# Debian Bullseye base (your image) — install yamllint via apt.
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  curl jq ca-certificates tar xz-utils python3 python3-pip yamllint

# hadolint (arch-aware static binary)
arch="$(uname -m)"
case "$arch" in
  x86_64)  HL_ARCH="x86_64" ;;
  aarch64|arm64) HL_ARCH="arm64" ;;
  *) echo "Unsupported arch: $arch" && exit 1 ;;
esac

# Pin if you want reproducibility. Leave empty to fetch 'latest'.
: "${HADOLINT_VERSION:=}"
if [[ -z "${HADOLINT_VERSION}" ]]; then
  HL_VER="$(curl -s https://api.github.com/repos/hadolint/hadolint/releases/latest \
    | jq -r '.tag_name')"
else
  HL_VER="v${HADOLINT_VERSION}"
fi

HL_URL="https://github.com/hadolint/hadolint/releases/download/${HL_VER}/hadolint-Linux-${HL_ARCH}"
sudo curl -sSL "${HL_URL}" -o /usr/local/bin/hadolint
sudo chmod +x /usr/local/bin/hadolint

# actionlint (official installer; also pin via ACTIONLINT_VERSION if desired)
: "${ACTIONLINT_VERSION:=}"
if [[ -z "${ACTIONLINT_VERSION}" ]]; then
  curl -sSL \
    https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash \
    | sudo bash -s -- -b /usr/local/bin
else
  curl -sSL \
    https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash \
    | sudo bash -s -- -b /usr/local/bin "v${ACTIONLINT_VERSION}"
fi

# Show versions for a quick sanity check.
echo "Installed versions:"
actionlint -version
yamllint --version
hadolint --version
