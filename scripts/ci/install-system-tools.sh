#!/usr/bin/env bash
set -euo pipefail

# Detect if we're running as root (devcontainer) or need sudo (host)
if [ "$(id -u)" -eq 0 ]; then
    SUDO_CMD=""
else
    SUDO_CMD="sudo"
fi

# Debian Bullseye base (your image) — install system dependencies via apt.
$SUDO_CMD apt-get update && $SUDO_CMD env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  curl jq ca-certificates tar xz-utils python3 python3-pip file


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

# yamlfmt (static binary from tarball, arch-aware)
# Uses the same architecture detection as hadolint
case "$arch" in
  x86_64)  YF_ARCH="x86_64" ;;
  aarch64|arm64) YF_ARCH="arm64" ;;
  *) echo "Unsupported arch: $arch" && exit 1 ;;
esac

# Optional pin (e.g., YAMLFMT_VERSION=0.12.0). Empty => latest.
: "${YAMLFMT_VERSION:=}"

if [[ -z "${YAMLFMT_VERSION}" ]]; then
    echo "Detecting latest yamlfmt version..."
    # Get latest release tag from redirect, then strip 'v'
    LATEST_TAG=$(curl -Ls -o /dev/null -w '%{url_effective}' "https://github.com/google/yamlfmt/releases/latest" | rev | cut -d'/' -f1 | rev)
    if [[ ! "$LATEST_TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Could not determine latest yamlfmt version from tag: ${LATEST_TAG}" >&2
        exit 1
    fi
    YAMLFMT_VERSION="${LATEST_TAG#v}"
    echo "Latest yamlfmt version is ${YAMLFMT_VERSION}"
fi

YF_TARBALL="yamlfmt_${YAMLFMT_VERSION}_Linux_${YF_ARCH}.tar.gz"
YF_URL="https://github.com/google/yamlfmt/releases/download/v${YAMLFMT_VERSION}/${YF_TARBALL}"

# Download, extract, and install
TMP_DIR=$(mktemp -d)
# Setup trap to remove temp dir on EXIT.
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Downloading yamlfmt from ${YF_URL}"
curl -fLso "${TMP_DIR}/${YF_TARBALL}" "${YF_URL}"

echo "Extracting yamlfmt binary"
tar -xzf "${TMP_DIR}/${YF_TARBALL}" -C "${TMP_DIR}" yamlfmt

echo "Installing yamlfmt to /usr/local/bin"
$SUDO_CMD mv "${TMP_DIR}/yamlfmt" /usr/local/bin/yamlfmt
$SUDO_CMD chmod +x /usr/local/bin/yamlfmt

if ! file /usr/local/bin/yamlfmt | grep -q 'ELF'; then
  echo "Installed yamlfmt is not a valid ELF. URL: ${YF_URL}" >&2
  exit 1
fi



# pyright and bandit are installed into the project's .venv by project Make targets.
# Ensure `make uv-sync-test` has been run. No system-wide install needed.

# Show versions for a quick sanity check.
echo "Installed versions:"
# Only print the first line of actionlint -version to avoid duplicate details
echo -n "actionlint: " && actionlint -version | head -n 1
echo -n "hadolint: " && hadolint --version
echo -n "yamlfmt: " && yamlfmt --version

echo -n "pyright: " && (
  if [ -f ".venv/bin/pyright" ]; then
    .venv/bin/pyright --version 2>/dev/null
  else
    echo "not installed (run: make uv-sync-test)"
  fi
)

echo -n "bandit: " && (
  if [ -f ".venv/bin/bandit" ]; then
    .venv/bin/bandit --version 2>/dev/null
  else
    echo "not installed (run: make uv-sync-test)"
  fi
)
