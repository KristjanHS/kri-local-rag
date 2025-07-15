# Use a slim Python base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# --- Install Dependencies ---
# Copy and install the lean, frontend-specific requirements
COPY frontend/requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

# --- Copy Application Code ---
# Copy the backend code so the frontend can import from it
COPY backend/ /app/backend/

# Copy the frontend app code
COPY frontend/ /app/frontend/

# Expose the default Streamlit port
EXPOSE 8501

# The command to run when the container starts
CMD ["streamlit", "run", "frontend/rag_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
