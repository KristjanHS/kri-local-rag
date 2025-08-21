##########
# Multi-stage build for smaller, production-focused image
##########

# ---------- Builder stage: resolve and install Python deps + package into a venv ----------
FROM python:3.12.3-slim AS builder

ENV VENV_PATH=/opt/venv
# Allow selecting PyTorch wheel channel (CPU by default). Examples:
# - CPU:   https://download.pytorch.org/whl/cpu
# - CUDA:  https://download.pytorch.org/whl/cu121
# - ROCm:  https://download.pytorch.org/whl/rocm6.1
ARG TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/cpu
ENV PIP_EXTRA_INDEX_URL=${TORCH_WHEEL_INDEX}
WORKDIR /app

# Create virtualenv and upgrade pip
RUN python -m venv ${VENV_PATH} \
    && ${VENV_PATH}/bin/pip install --upgrade pip

# Install runtime dependencies into venv
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    ${VENV_PATH}/bin/pip install -r requirements.txt

# Install our backend package (non-editable) into the venv
COPY pyproject.toml ./
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
RUN ${VENV_PATH}/bin/pip install .

# Download required NLTK data for UnstructuredMarkdownLoader
# Using dedicated script for robust download with proper error handling
ENV NLTK_DATA=${VENV_PATH}/nltk_data
COPY scripts/download_nltk_data.py /tmp/
RUN ${VENV_PATH}/bin/python /tmp/download_nltk_data.py ${NLTK_DATA} \
    && rm /tmp/download_nltk_data.py


# ---------- Final stage: minimal runtime with only what we need ----------
FROM python:3.12.3-slim

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"
# NLTK data location (copied from builder stage)
ENV NLTK_DATA=${VENV_PATH}/nltk_data

WORKDIR /app

# OS runtime dependencies only (no dev/build tools)
# Security strategy: Use apt-get upgrade for security updates rather than pinning specific versions
# This allows security patches while maintaining build reproducibility through base image pinning
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    wget \
    libmagic1 \
    poppler-utils \
    tesseract-ocr tesseract-ocr-eng \
    libgl1 libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Bring in the prebuilt virtualenv from the builder stage
COPY --from=builder ${VENV_PATH} ${VENV_PATH}

# Copy application assets that are not part of the Python package
COPY frontend/ /app/frontend/
COPY example_data/ /app/example_data/

# Runtime tuning (safe defaults for CPU-only deployments)
ENV OMP_NUM_THREADS=6
ENV MKL_NUM_THREADS=6
ENV DNNL_PRIMITIVE_CACHE_CAPACITY=1024

EXPOSE 8501

# Non-root user and permissions
RUN useradd -ms /bin/bash appuser \
    && chown -R appuser:appuser /app /app/example_data \
    && mkdir -p /root/.ollama \
    && chown -R appuser:appuser /root/.ollama
USER appuser

CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0"]