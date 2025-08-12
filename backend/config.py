import logging
import logging.handlers
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from the project root .env (if present)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# --- Logging Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_logging_configured = False


def _resolve_log_dir() -> Path:
    """Return a writable log directory.
    Order of preference:
    1) APP_LOG_DIR env
    2) LOG_DIR env
    3) /app/logs (Docker runtime)
    4) CWD/logs (dev)
    5) /tmp/logs (always writable)
    """
    candidate_strings = [
        os.getenv("APP_LOG_DIR"),
        os.getenv("LOG_DIR"),
        "/app/logs",
        str(Path.cwd() / "logs"),
        "/tmp/logs",
    ]

    for candidate in candidate_strings:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        try:
            candidate_path.mkdir(parents=True, exist_ok=True)
            return candidate_path
        except PermissionError:
            continue

    # Fallback that should always work
    fallback = Path("/tmp/logs")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _setup_logging():
    """Configure the root logger. This should only be called once."""
    global _logging_configured
    if _logging_configured:
        return

    log_dir = _resolve_log_dir()
    log_file = log_dir / "rag_system.log"

    # Use a rotating file handler to prevent log files from growing indefinitely
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,  # 10 MB per file, 5 backups
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Use stderr for console logging
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Suppress detailed HTTP request logging from httpx while keeping important info
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Suppress verbose logging from other libraries
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified module name.
    Initializes logging on first call.
    """
    if not _logging_configured:
        _setup_logging()
    return logging.getLogger(name)


# --- End Logging Configuration ---


COLLECTION_NAME = "Document"

# Text splitting parameters
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Hybrid search parameters
DEFAULT_HYBRID_ALPHA = 0.5  # 0 → pure BM25, 1 → pure vector
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# Ollama LLM settings (used by qa_loop.py)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "cas/mistral-7b-instruct-v0.3")
# Default to local Ollama endpoint but allow override via env variable.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")

# If running in a Docker container, use the service name
if os.getenv("DOCKER_ENV"):
    OLLAMA_URL = "http://ollama:11434"
    WEAVIATE_URL = "http://weaviate:8080"

# Default context window (max tokens) for Ollama LLM requests
OLLAMA_CONTEXT_TOKENS = int(os.getenv("OLLAMA_CONTEXT_TOKENS", 8192))  # e.g. 4096, 8192, etc.


# (base) PS C:\Users\PC> ollama show cas/mistral-7b-instruct-v0.3
#  Model
#    architecture        llama3
#    context length      32768
#    embedding length    4096
#    quantization        Q4_K_M
