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

# B8: verify a downloaded file against an expected SHA256 before installing.
# Pins below default to known-good versions; checksums are fetched from each
# release's published checksum manifest and compared. Override *_VERSION to bump.
verify_sha256() {
  # $1 = file path, $2 = expected lowercase hex sha256
  local file="$1" expected="$2" actual
  actual="$(sha256sum "$file" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "SHA256 mismatch for ${file}" >&2
    echo "  expected: ${expected}" >&2
    echo "  actual:   ${actual}" >&2
    exit 1
  fi
}

# --- hadolint (static binary, arch-aware) ---
arch="$(uname -m)"
case "$arch" in
  x86_64)  HL_ARCH="x86_64" ;;
  aarch64|arm64) HL_ARCH="arm64" ;;
  *) echo "Unsupported arch: $arch" && exit 1 ;;
esac

# Pinned for supply-chain integrity (B8). Override via HADOLINT_VERSION.
: "${HADOLINT_VERSION:=2.14.0}"

# Versioned download URL (avoids the GitHub API to dodge 403s). Lowercase asset
# names match the published checksum sidecar.
HL_URL="https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-linux-${HL_ARCH}"

# Download fresh into a temp file, verify SHA256, then install.
HL_TMP="$(mktemp)"
trap 'rm -f "$HL_TMP"' EXIT
curl -fLso "$HL_TMP" "${HL_URL}"
# The .sha256 sidecar is "<hash> *<filename>"; take field 1 as the expected hash.
HL_EXPECTED="$(curl -fsSL "${HL_URL}.sha256" | awk '{print $1}')"
verify_sha256 "$HL_TMP" "$HL_EXPECTED"
$SUDO_CMD rm -f /usr/local/bin/hadolint
$SUDO_CMD install -m 0755 "$HL_TMP" /usr/local/bin/hadolint
rm -f "$HL_TMP"
trap - EXIT
if ! file /usr/local/bin/hadolint | grep -q 'ELF'; then
  echo "Installed hadolint is not a valid ELF. URL: ${HL_URL}" >&2
  exit 1
fi

# --- actionlint (static binary from tarball, arch-aware) ---
# Pinned + checksum-verified (B8). Replaces the previously unpinned
# download-actionlint.bash fetched from the repo's main branch.
case "$arch" in
  x86_64)  AL_ARCH="amd64" ;;
  aarch64|arm64) AL_ARCH="arm64" ;;
  *) echo "Unsupported arch: $arch" && exit 1 ;;
esac

: "${ACTIONLINT_VERSION:=1.7.12}"

AL_TARBALL="actionlint_${ACTIONLINT_VERSION}_linux_${AL_ARCH}.tar.gz"
AL_BASE="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}"
AL_URL="${AL_BASE}/${AL_TARBALL}"
AL_CHECKSUMS_URL="${AL_BASE}/actionlint_${ACTIONLINT_VERSION}_checksums.txt"

AL_TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$AL_TMP_DIR"' EXIT
echo "Downloading actionlint from ${AL_URL}"
curl -fLso "${AL_TMP_DIR}/${AL_TARBALL}" "${AL_URL}"
# checksums.txt lines are "<hash>  <filename>"; match our tarball's row.
AL_EXPECTED="$(curl -fsSL "${AL_CHECKSUMS_URL}" | awk -v f="${AL_TARBALL}" '$2==f {print $1}')"
if [[ -z "${AL_EXPECTED}" ]]; then
  echo "No checksum entry for ${AL_TARBALL} in ${AL_CHECKSUMS_URL}" >&2
  exit 1
fi
verify_sha256 "${AL_TMP_DIR}/${AL_TARBALL}" "${AL_EXPECTED}"
tar -xzf "${AL_TMP_DIR}/${AL_TARBALL}" -C "${AL_TMP_DIR}" actionlint
$SUDO_CMD install -m 0755 "${AL_TMP_DIR}/actionlint" /usr/local/bin/actionlint
rm -rf "$AL_TMP_DIR"
trap - EXIT

# --- yamlfmt (static binary from tarball, arch-aware) ---
case "$arch" in
  x86_64)  YF_ARCH="x86_64" ;;
  aarch64|arm64) YF_ARCH="arm64" ;;
  *) echo "Unsupported arch: $arch" && exit 1 ;;
esac

# Pinned + checksum-verified (B8). Override via YAMLFMT_VERSION.
: "${YAMLFMT_VERSION:=0.21.0}"

YF_TARBALL="yamlfmt_${YAMLFMT_VERSION}_Linux_${YF_ARCH}.tar.gz"
YF_BASE="https://github.com/google/yamlfmt/releases/download/v${YAMLFMT_VERSION}"
YF_URL="${YF_BASE}/${YF_TARBALL}"
YF_CHECKSUMS_URL="${YF_BASE}/checksums.txt"

YF_TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$YF_TMP_DIR"' EXIT
echo "Downloading yamlfmt from ${YF_URL}"
curl -fLso "${YF_TMP_DIR}/${YF_TARBALL}" "${YF_URL}"
# checksums.txt lines are "<hash>  <filename>"; match our tarball's row.
YF_EXPECTED="$(curl -fsSL "${YF_CHECKSUMS_URL}" | awk -v f="${YF_TARBALL}" '$2==f {print $1}')"
if [[ -z "${YF_EXPECTED}" ]]; then
  echo "No checksum entry for ${YF_TARBALL} in ${YF_CHECKSUMS_URL}" >&2
  exit 1
fi
verify_sha256 "${YF_TMP_DIR}/${YF_TARBALL}" "${YF_EXPECTED}"
echo "Extracting yamlfmt binary"
tar -xzf "${YF_TMP_DIR}/${YF_TARBALL}" -C "${YF_TMP_DIR}" yamlfmt
$SUDO_CMD install -m 0755 "${YF_TMP_DIR}/yamlfmt" /usr/local/bin/yamlfmt
rm -rf "$YF_TMP_DIR"
trap - EXIT
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
