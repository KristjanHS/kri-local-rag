FROM python:3.12.3-slim

ENV PYTHONUNBUFFERED=1

# Suppress pip sudo warnings - no need for .venv in production dockerfile
ENV PIP_ROOT_USER_ACTION=ignore

# Suppress update-alternatives warnings - they are normal in python slim images
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app/backend

# System deps required by PDF parsing & other libs.
RUN apt-get update && \
# Apply latest OS security patches, then install required packages
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        libmagic1 libmagic-dev \
        poppler-utils \
        tesseract-ocr libtesseract-dev \
        ghostscript \
        libgl1 libglib2.0-0 \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---- wheel cache mount (optional) ----
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128

# ---- rest of your deps ----
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
    # pip install --no-cache-dir -r requirements.txt
    # If you do not need GPU inside this container, ALSO remove the runtime line in docker-compose.yml!
    # Enable GPU support via NVIDIA runtime (CUDA libraries are provided by the host runtime)
    # Optional: install GPU-enabled PyTorch (comment out if you prefer CPU)

# Copy source code last (so edits don’t invalidate earlier layers)
COPY backend/ /app/backend/

# Also copy the example data so it's available for auto-ingestion at /example_data
COPY example_data/ /example_data/

# Default command – override in docker-compose if you need another entrypoint.
CMD ["python", "qa_loop.py"] 