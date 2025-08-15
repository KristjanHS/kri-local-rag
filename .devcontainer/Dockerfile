# Use the official Microsoft dev container image as a base.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Switch to root to install system-level dependencies.
USER root

# Set environment variables for pinned tool versions to ensure reproducibility.
# These can be overridden at build time if needed.
ARG HADOLINT_VERSION=2.12.0
ARG ACTIONLINT_VERSION=1.7.1

# Combine package installation and cleanup into a single RUN layer to reduce image size.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    ca-certificates \
    tar \
    xz-utils \
    python3 \
    python3-pip \
    yamllint \
    file \
    && rm -rf /var/lib/apt/lists/*

# Install hadolint (static binary, arch-aware).
RUN arch="$(uname -m)" && \
    case "$arch" in \
    x86_64)  HL_ARCH="x86_64" ;; \
    aarch64|arm64) HL_ARCH="arm64" ;; \
    *) echo "Unsupported arch: $arch" && exit 1 ;; \
    esac && \
    curl -fLso /usr/local/bin/hadolint "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-${HL_ARCH}" && \
    chmod +x /usr/local/bin/hadolint

# Install actionlint using its official download script.
RUN curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash | bash -s -- -b /usr/local/bin "${ACTIONLINT_VERSION}"

# Switch back to the non-root user for subsequent commands and for the final container environment.
USER vscode
