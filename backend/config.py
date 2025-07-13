from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from the project root .env (if present)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

COLLECTION_NAME = "Document"

# Text splitting parameters
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Hybrid search parameters
DEFAULT_HYBRID_ALPHA = 0.5  # 0 → pure BM25, 1 → pure vector

# Ollama LLM settings (used by qa_loop.py)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "cas/mistral-7b-instruct-v0.3")
# Default to local Ollama endpoint but allow override via env variable.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
