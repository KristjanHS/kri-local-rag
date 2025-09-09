# syntax=docker/dockerfile:1.7
##########
# Two-stage build: builder (Python deps) → runtime (OS deps + app)
##########

############################
# Build stage: wheels/venv #
############################
# Pin this image by digest in CI for full reproducibility.
# Example: python:3.12-slim-bookworm@sha256:...
FROM python:3.12-slim-bookworm AS builder

ENV VENV_PATH=/opt/venv \
  PIP_DISABLE_PIP_VERSION_CHECK=1
ARG INSTALL_DEV=0

WORKDIR /app

# Copy only files needed for package installation (not mounted app code)
COPY requirements.txt ./
COPY requirements-dev.txt ./
COPY pyproject.toml ./
COPY README.md ./
COPY cli.py .

# Create venv and upgrade pip
RUN python -m venv ${VENV_PATH} \
  && ${VENV_PATH}/bin/pip install --upgrade pip

# Pre-install runtime deps for cache friendliness unless doing a dev build
# - For regular builds (INSTALL_DEV=0): install runtime reqs now for better cache reuse
# - For dev/test builds (INSTALL_DEV=1): skip here to avoid double-install (dev reqs include runtime)
RUN --mount=type=cache,target=/root/.cache/pip \
  if [ "${INSTALL_DEV}" = "1" ]; then \
  echo "Skipping requirements.txt preinstall for dev build"; \
  else \
  ${VENV_PATH}/bin/pip install -r requirements.txt; \
  fi

# Install our package and optionally dev deps
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
RUN --mount=type=cache,target=/root/.cache/pip \
  if [ "${INSTALL_DEV}" = "1" ]; then \
  ${VENV_PATH}/bin/pip install -r requirements-dev.txt; \
  else \
  ${VENV_PATH}/bin/pip install .; \
  fi

############################################
# Runtime stage: Debian + apt + your app  #
############################################
FROM python:3.12-slim-bookworm AS runtime

# --- Debian snapshot date (set to base image date in CI) ---
# Accepts YYYYMMDD or YYYYMMDDTHHMMSSZ. Example default is a placeholder.
ARG SNAPSHOT=20250906T000000Z  # Bookworm 12.12 point release date

# Replace sources with a single Deb822 file pointing to snapshot.debian.org.
# Ensure SNAPSHOT is expanded by the shell (avoid quoted heredoc preventing expansion).
RUN set -eux; \
  rm -f /etc/apt/sources.list; \
  printf '%s\n' \
    'Types: deb' \
    "URIs: https://snapshot.debian.org/archive/debian/${SNAPSHOT}/" \
    'Suites: bookworm bookworm-updates' \
    'Components: main contrib non-free non-free-firmware' \
    'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
    'Check-Valid-Until: no' \
    '' \
    'Types: deb' \
    "URIs: https://snapshot.debian.org/archive/debian-security/${SNAPSHOT}/" \
    'Suites: bookworm-security' \
    'Components: main contrib non-free non-free-firmware' \
    'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
    'Check-Valid-Until: no' \
  > /etc/apt/sources.list.d/debian.sources

# Install OS runtime deps (single RUN; clean lists)
# hadolint ignore=DL3008
# Snapshot URLs pin package set; explicit versions unnecessary
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update && \
  apt-get install -y --no-install-recommends \
  ca-certificates wget libmagic1 poppler-utils \
  tesseract-ocr tesseract-ocr-eng \
  libgl1 libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Python tuning
ENV VENV_PATH=/opt/venv
# hadolint ignore=SC2269
# Intentionally prepend venv bin to PATH while preserving base PATH
ENV PATH="${VENV_PATH}/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1
# Runtime tuning: safe defaults for CPU-only deployments
ENV OMP_NUM_THREADS=6 \
  MKL_NUM_THREADS=6 \
  DNNL_PRIMITIVE_CACHE_CAPACITY=1024
# Model caching configuration
ENV HF_HOME=/data/hf
# Streamlit runtime tuning
ENV STREAMLIT_SERVER_HEADLESS=true \
  STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Bring in the prebuilt venv (same Python ABI as runtime base)
COPY --from=builder "${VENV_PATH}" "${VENV_PATH}"

# App assets not included in the sdist/wheel
COPY frontend/ /app/frontend/
COPY example_data/ /app/example_data/

EXPOSE 8501

# Container-native healthcheck for Streamlit readiness
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=30 \
  CMD wget -q --spider http://localhost:8501/_stcore/health || exit 1

# Create non-root user and directories, and set permissions
RUN useradd -ms /bin/bash appuser \
  && mkdir -p backend frontend data logs /data/hf \
  && chown -R appuser:appuser /app /data

USER appuser

# Sanity check: prove streamlit exists & is runnable (fails build if not)
RUN test -x "${VENV_PATH}/bin/streamlit" \
  && "${VENV_PATH}/bin/python" -c "import streamlit, sys; print(streamlit.__version__)"

# Launch Streamlit via the venv Python to avoid PATH ambiguity
CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
