from pathlib import Path
from dotenv import load_dotenv
import os
import logging
import sys

# Load environment variables from the project root .env (if present)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Create logs directory if it doesn't exist
log_dir = Path(__file__).resolve().parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_dir / "rag_system.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Suppress detailed HTTP request logging from httpx while keeping important info
logging.getLogger("httpx").setLevel(logging.WARNING)

# Also suppress other HTTP-related verbose logging
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# Suppress verbose logging from other libraries during ingestion
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("torch").setLevel(logging.WARNING)


# Create module-specific loggers
def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module name."""
    return logging.getLogger(name)


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
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")

# Default context window (max tokens) for Ollama LLM requests
OLLAMA_CONTEXT_TOKENS = int(
    os.getenv("OLLAMA_CONTEXT_TOKENS", 8192)
)  # e.g. 4096, 8192, etc.


# (base) PS C:\Users\PC> ollama show cas/mistral-7b-instruct-v0.3
#  Model
#    architecture        llama3
#    context length      32768
#    embedding length    4096
#    quantization        Q4_K_M
