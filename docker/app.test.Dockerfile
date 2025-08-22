# Dockerfile for the test environment

# ---------- Models stage: fetch pinned model snapshots (shared with main Dockerfile) ----------
FROM python:3.12.3-slim AS models

# Install minimal dependencies for model downloading
RUN pip install --no-cache-dir pip==24.2 \
    && pip install --no-cache-dir huggingface_hub==0.34.4

# Download models with pinned commits (same as main Dockerfile)
ARG EMBEDDING_MODEL EMBED_COMMIT RERANK_MODEL RERANK_COMMIT
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL:-sentence-transformers/all-MiniLM-L6-v2}
ENV RERANK_MODEL=${RERANK_MODEL:-cross-encoder/ms-marco-MiniLM-L-6-v2}
ENV EMBED_COMMIT=${EMBED_COMMIT}
ENV RERANK_COMMIT=${RERANK_COMMIT}

COPY scripts/download_models.py /tmp/download_models.py
RUN mkdir -p /models/emb /models/rerank \
    && python /tmp/download_models.py \
    && rm /tmp/download_models.py

# ---------- Builder stage for tests: install all dependencies into a venv ----------
FROM python:3.12.3-slim AS builder-test

ENV VENV_PATH=/opt/venv
ARG TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/cpu
ENV PIP_EXTRA_INDEX_URL=${TORCH_WHEEL_INDEX}
WORKDIR /app

# Copy downloaded models from models stage for testing
COPY --from=models /models /models

# Copy only files needed for package installation (not mounted app code)
COPY requirements.txt .
COPY pyproject.toml .
COPY requirements-dev.txt .
COPY README.md .
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
COPY scripts/download_nltk_data.py /tmp/
RUN ${VENV_PATH}/bin/python /tmp/download_nltk_data.py ${NLTK_DATA} \
    && rm /tmp/download_nltk_data.py

# ---------- Final stage for tests: minimal runtime with test dependencies ----------
FROM python:3.12.3-slim

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"
# NLTK data location (copied from builder stage)
ENV NLTK_DATA=${VENV_PATH}/nltk_data

WORKDIR /app

# OS runtime dependencies
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

# Bring in the prebuilt virtualenv from the builder-test stage
COPY --from=builder-test ${VENV_PATH} ${VENV_PATH}

# Copy downloaded models from the builder-test stage for testing
COPY --from=builder-test /models /models

# Copy static assets (these will be overridden by volume mounts in development)
COPY example_data/ /app/example_data/

# Model configuration for flexible testing (supports both offline and online modes)
# Tests can override these environment variables as needed
ENV SENTENCE_TRANSFORMERS_HOME=/models
ENV EMBED_MODEL_PATH=/models/emb
ENV RERANK_MODEL_PATH=/models/rerank
ENV HF_HOME=/data/hf
# Leave TRANSFORMERS_OFFLINE unset by default for flexible testing
# Tests can set TRANSFORMERS_OFFLINE=1 for offline testing

# Create directories and set up user
RUN mkdir -p backend frontend tests data logs \
    && mkdir -p /data/hf \
    && useradd -ms /bin/bash appuser \
    && mkdir -p /root/.ollama \
    && chown -R appuser:appuser /app /app/example_data /root/.ollama /data
USER appuser
