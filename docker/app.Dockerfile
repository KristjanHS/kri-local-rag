##########
# Multi-stage build for smaller, production-focused image
##########

# ---------- Base stage: common OS dependencies ----------
FROM python:3.12.3-slim AS base

# OS runtime dependencies only (no dev/build tools)
# Use pinned versions for better reproducibility while maintaining security
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    wget=1.21.3-1+deb12u1 \
    libmagic1=1:5.44-3 \
    poppler-utils=22.12.0-2+deb12u1 \
    tesseract-ocr=5.3.0-2 \
    tesseract-ocr-eng=1:4.1.0-2 \
    libgl1=1.6.0-1 \
    libglib2.0-0=2.74.6-2+deb12u6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------- Models downloaded at runtime using HuggingFace caching ----------

# ---------- Builder stage: resolve and install Python deps + package into a venv ----------
FROM python:3.12.3-slim AS builder

ENV VENV_PATH=/opt/venv
ARG TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/cpu
ENV PIP_EXTRA_INDEX_URL=${TORCH_WHEEL_INDEX}
WORKDIR /app

# Copy only files needed for package installation (not mounted app code)
COPY requirements.txt ./
COPY pyproject.toml ./
COPY README.md ./
COPY cli.py .

# Create virtualenv and upgrade pip
RUN python -m venv ${VENV_PATH} \
    && ${VENV_PATH}/bin/pip install --upgrade pip

# Install runtime dependencies into venv
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
COPY scripts/dev/download_nltk_data.py /tmp/
RUN ${VENV_PATH}/bin/python /tmp/download_nltk_data.py ${NLTK_DATA} \
    && rm /tmp/download_nltk_data.py


# ---------- Final stage for Production: minimal runtime with only what we need ----------
FROM base AS prod

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

EXPOSE 8501

# Create non-root user and directories, and set permissions
RUN useradd -ms /bin/bash appuser \
    && mkdir -p backend frontend data logs /data/hf \
    && chown -R appuser:appuser /app /data

USER appuser

CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ---------- Builder stage for tests: install all dependencies into a venv ----------
FROM python:3.12.3-slim AS builder-test

ENV VENV_PATH=/opt/venv
ARG TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/cpu
ENV PIP_EXTRA_INDEX_URL=${TORCH_WHEEL_INDEX}
WORKDIR /app

# Copy only files needed for package installation (not mounted app code)
COPY requirements.txt ./
COPY requirements-dev.txt ./
COPY pyproject.toml ./
COPY README.md ./
COPY cli.py .

# Create virtualenv, upgrade pip, create directories, and install dependencies
RUN python -m venv ${VENV_PATH} \
    && ${VENV_PATH}/bin/pip install --upgrade pip \
    && mkdir -p backend frontend \
    && ${VENV_PATH}/bin/pip install -r requirements.txt \
    && ${VENV_PATH}/bin/pip install -r requirements-dev.txt \
    && ${VENV_PATH}/bin/pip install -e .

# Download required NLTK data for UnstructuredMarkdownLoader
# Using dedicated script for robust download with proper error handling
ENV NLTK_DATA=${VENV_PATH}/nltk_data
COPY scripts/dev/download_nltk_data.py /tmp/
RUN ${VENV_PATH}/bin/python /tmp/download_nltk_data.py ${NLTK_DATA} \
    && rm /tmp/download_nltk_data.py

# ---------- Final stage for Testing: minimal runtime with test dependencies ----------
FROM base AS test

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"
# NLTK data location (copied from builder-test stage)
ENV NLTK_DATA=${VENV_PATH}/nltk_data

WORKDIR /app

# Bring in the prebuilt virtualenv from the builder-test stage
COPY --from=builder-test ${VENV_PATH} ${VENV_PATH}

# Copy static assets (these will be overridden by volume mounts in development)
COPY example_data/ /app/example_data/

# Model caching for testing
ENV HF_HOME=/data/hf

# Create directories and set up user
RUN mkdir -p backend frontend tests data logs \
    && mkdir -p /data/hf \
    && useradd -ms /bin/bash appuser \
    && mkdir -p /root/.ollama \
    && chown -R appuser:appuser /app /app/example_data /root/.ollama /data /models
USER appuser

# Keep container alive for exec commands without starting the web server
CMD ["tail", "-f", "/dev/null"]