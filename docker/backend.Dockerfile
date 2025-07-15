FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Suppress pip sudo warnings - no need for .venv in production dockerfile
ENV PIP_ROOT_USER_ACTION=ignore

# Suppress update-alternatives warnings - they are normal in python slim images
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app/backend

# System deps required by PDF parsing & other libs.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements separately to leverage Docker layer cache
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    # If you do not need GPU inside this container, ALSO remove the runtime line in docker-compose.yml!
    # Enable GPU support via NVIDIA runtime (CUDA libraries are provided by the host runtime)
    # Optional: install GPU-enabled PyTorch (comment out if you prefer CPU)
    pip install --no-cache-dir torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128 || true

# Copy source code last (so edits don’t invalidate earlier layers)
COPY backend/ /app/backend/

# Also copy the example data so it's available for auto-ingestion
COPY example_data/ /app/example_data/

# Default command – override in docker-compose if you need another entrypoint.
CMD ["python", "qa_loop.py"] 