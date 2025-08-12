##########
# Multi-stage build for smaller, production-focused image
##########

# ---------- Builder stage: resolve and install Python deps + package into a venv ----------
FROM python:3.12.3-slim AS builder

ENV VENV_PATH=/opt/venv
# Use CPU-only PyTorch wheels in builds to avoid heavy CUDA deps and failures
ENV PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu
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
RUN ${VENV_PATH}/bin/pip install .


# ---------- Final stage: minimal runtime with only what we need ----------
FROM python:3.12.3-slim

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR /app

# OS runtime dependencies only (no dev/build tools)
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
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
COPY example_data/ /example_data/

# Runtime tuning (safe defaults for CPU-only deployments)
ENV OMP_NUM_THREADS=6
ENV MKL_NUM_THREADS=6
ENV DNNL_PRIMITIVE_CACHE_CAPACITY=1024

EXPOSE 8501

# Non-root user and permissions
RUN useradd -ms /bin/bash appuser \
    && chown -R appuser:appuser /app /example_data
USER appuser

CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0"]