# Use a slim Python base image
FROM python:3.12.3-slim

# Set the working directory inside the container
WORKDIR /app

# --- Install Dependencies ---
# First, pull in latest security patches for the base image
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends libmagic1 libmagic-dev && \
    apt-get install -y --no-install-recommends poppler-utils && \
    # Install tesseract for OCR (required by unstructured[pdf])
    apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && \
    # Needed by OpenCV (dependency of unstructured)
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- upgrade pip ----
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip

# PyTorch (CPU-only) and sentence-transformers are now installed via requirements.txt (which points
# pip to the CPU wheels using an --extra-index-url directive), so no separate install command is
# necessary here.


# ---- rest of your deps ----
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
    
# ---- dev deps ----
COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt
    
COPY pyproject.toml .
RUN pip install -e .

# --- Copy Application Code ---
# Copy the backend code so the app can import from it
COPY backend/ /app/backend/

# Copy the frontend app code
COPY frontend/ /app/frontend/

# Copy example data for initial Weaviate warm-up
COPY example_data/ /example_data/

# Set CPU optimization environment variables
# OMP_NUM_THREADS: one OpenMP thread per core for running many small models
ENV OMP_NUM_THREADS=6
# MKL threading for Intel CPU optimizations
ENV MKL_NUM_THREADS=6
# Enable oneDNN optimizations
ENV DNNL_PRIMITIVE_CACHE_CAPACITY=1024

# Expose the default Streamlit port
EXPOSE 8501

# The command to run when the container starts
CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0"] 