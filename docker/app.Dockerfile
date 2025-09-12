# syntax=docker/dockerfile:1.7
##########
# Two-stage build: builder (Python deps via uv) → runtime (OS deps + app)
##########

############################
# Build stage: wheels/venv #
############################

# Pin this image by digest in CI for full reproducibility.
# Example: python:3.12-slim-bookworm@sha256:...
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV VENV_PATH=/opt/venv \
  UV_PROJECT_ENVIRONMENT=/opt/venv \
  UV_LINK_MODE=copy

# ENV UV_COMPILE_BYTECODE=1
# Precompile imported .py files into .pyc as it installs/syncs
# But if you run with editable installs or generate .py at runtime, drop UV_COMPILE_BYTECODE at Build stage

WORKDIR /app

# uv phase 1 (to optimize uv cache use): install ONLY deps (lockfile-driven) into /opt/venv
#    (Copy only files needed for dependency resolution)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
  uv sync --locked --no-install-project --no-dev

# uv phase 2: copy project and install the project as package

# Copy only backend/ and cli.py that will be packaged here.
# NB! frontend/ will be referenced as folder in runtime image, so it will be copied in runtime stage below
COPY backend/ /app/backend/
COPY cli.py /app/

# INSTALL_DEV toggles dev/test groups for CI/dev images, and make project package editable
ARG INSTALL_DEV=0
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
  if [ "$INSTALL_DEV" = "1" ]; then \
  uv sync --locked --group dev --group test; \
  else \
  uv sync --locked --no-editable --no-dev; \
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
ENV PYTHONUNBUFFERED=1
# Unbuffered: Forces unbuffered stdout/stderr (same as python -u) so logs show up immediately in Docker.

# ENV PYTHONDONTWRITEBYTECODE=1 \
# DontwriteBytecode: re-use the bytecode that was compiled by uv during Build phase
# But if you run with editable installs or generate .py at runtime, drop PYTHONDONTWRITEBYTECODE at Runtime stage

# Runtime tuning: safe defaults for CPU-only deployments
ENV OMP_NUM_THREADS=6 \
  MKL_NUM_THREADS=6 \
  DNNL_PRIMITIVE_CACHE_CAPACITY=1024
# Streamlit runtime tuning
ENV STREAMLIT_SERVER_HEADLESS=true \
  STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Bring in the prebuilt venv (same Python ABI as runtime base)
COPY --from=builder "${VENV_PATH}" "${VENV_PATH}"

WORKDIR /app
ENV HOME=/home/appuser
# Create a real non-root user with home, into the conventional /home/<username>
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g ${APP_GID} appgroup && \
  useradd -l -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash appuser

# Huggingface models cache that lives inside the image or named volume
# TODO: make a named volume for persistance of HF cache
ENV HF_HOME=/hf_cache

# NB! Never rely on chown in the image for bind mounts. A bind mount hides whatever you COPY/chowned at
# build-time and writes go back to the host filesystem. Instead, pre-create/own the host directories.

# Create folders and set permission for non-root user - this works for named volumes or image content
RUN mkdir --chown=appuser:appgroup -p /hf_cache /app /home/appuser

# Ship the folders that Prod needs, in the image (in Dev, these are hidden by bind mount)
COPY --chown=appuser:appgroup frontend/ /app/frontend/
COPY --chown=appuser:appgroup example_data/ /app/example_data/

USER appuser

EXPOSE 8501
# Container-native healthcheck for Streamlit readiness
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=30 \
  CMD wget -q --spider http://localhost:8501/_stcore/health || exit 1

# Sanity check: prove streamlit exists & is runnable (fails build if not)
# Also print the version and a simple format explanation
RUN test -x "${VENV_PATH}/bin/streamlit" \
  && "${VENV_PATH}/bin/python" -c \
  "import streamlit; v = streamlit.__version__; print(v)" \
  && "${VENV_PATH}/bin/python" -c \
  "print('Format: major.minor.patch (breaking, features, fixes)')"

ENV STREAMLIT_SERVER_PORT=8501 \
  STREAMLIT_SERVER_ADDRESS=0.0.0.0
# Auto-start Streamlit when container starts (headless + no telemetry)
CMD ["/opt/venv/bin/streamlit", "run", "frontend/rag_app.py", "--server.headless=true", "--browser.gatherUsageStats=false"]
# NB! ENV variables like ${VENV_PATH} are NOT expanded inside JSON-array CMD or ENTRYPOINT.
