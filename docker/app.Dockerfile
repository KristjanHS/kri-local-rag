# Use a slim Python base image
FROM python:3.12.3-slim

# Set the working directory inside the container
WORKDIR /app

# --- Install Dependencies ---
# First, pull in latest security patches for the base image
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends libmagic1 libmagic-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- wheel cache mount (optional) ----
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128

# ---- rest of your deps ----
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt
    # If you do not need GPU inside this container, ALSO remove the runtime line in docker-compose.yml!
    # Enable GPU support via NVIDIA runtime (CUDA libraries are provided by the host runtime)
    # Optional: install GPU-enabled PyTorch (comment out if you prefer CPU)
    
# --- Copy Application Code ---
# Copy the backend code so the app can import from it
COPY backend/ /app/backend/

# Copy the frontend app code
COPY frontend/ /app/frontend/

# Copy example data for initial Weaviate warm-up
COPY example_data/ /example_data/

# Expose the default Streamlit port
EXPOSE 8501

# The command to run when the container starts
CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0"] 