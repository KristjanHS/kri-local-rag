# syntax=docker/dockerfile:1.7
##########
# Two-stage build: builder (Python deps) → runtime (OS deps + app)
##########

# ---------- Builder stage: resolve and install Python deps + package into a venv ----------
FROM python:3.12.3-slim AS builder

ENV VENV_PATH=/opt/venv
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
ARG INSTALL_DEV=0
WORKDIR /app

# Copy only files needed for package installation (not mounted app code)
COPY requirements.txt ./
COPY requirements-dev.txt ./
COPY pyproject.toml ./
COPY README.md ./
COPY cli.py .

# Create virtualenv and upgrade pip
RUN python -m venv ${VENV_PATH} \
    && ${VENV_PATH}/bin/pip install --upgrade pip

# Install runtime (and optionally dev) dependencies into venv in one layer
RUN --mount=type=cache,target=/root/.cache/pip \
    ${VENV_PATH}/bin/pip install -r requirements.txt \
    && if [ "${INSTALL_DEV}" = "1" ]; then ${VENV_PATH}/bin/pip install -r requirements-dev.txt; fi

# Install our backend package (non-editable) into the venv
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
RUN ${VENV_PATH}/bin/pip install .

# Download required NLTK data for UnstructuredMarkdownLoader
ENV NLTK_DATA=${VENV_PATH}/nltk_data
COPY scripts/dev/download_nltk_data.py /tmp/
RUN ${VENV_PATH}/bin/python /tmp/download_nltk_data.py ${NLTK_DATA} \
    && rm /tmp/download_nltk_data.py


# ---------- Final runtime stage: minimal runtime with only what we need ----------
FROM python:3.12.3-slim AS runtime

# Install OS runtime dependencies (unpinned to avoid snapshot churn)
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
       wget \
       libmagic1 \
       poppler-utils \
       tesseract-ocr \
       tesseract-ocr-eng \
       libgl1 \
       libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"
# NLTK data location (copied from builder stage)
ENV NLTK_DATA=${VENV_PATH}/nltk_data

WORKDIR /app

# Bring in the prebuilt virtualenv from the builder stage
COPY --from=builder ${VENV_PATH} ${VENV_PATH}

# Copy application assets that are not part of the Python package
COPY frontend/ /app/frontend/
COPY example_data/ /app/example_data/

# Runtime tuning (safe defaults for CPU-only deployments)
ENV OMP_NUM_THREADS=6
ENV MKL_NUM_THREADS=6
ENV DNNL_PRIMITIVE_CACHE_CAPACITY=1024

# Model caching configuration
ENV HF_HOME=/data/hf
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

# Container-native healthcheck for Streamlit readiness
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=30 \
  CMD wget -q --spider http://localhost:8501/_stcore/health || exit 1

# Create non-root user and directories, and set permissions
RUN useradd -ms /bin/bash appuser \
    && mkdir -p backend frontend data logs /data/hf \
    && chown -R appuser:appuser /app /data

USER appuser

CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
