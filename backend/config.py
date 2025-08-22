import logging
import logging.handlers
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from rich.logging import RichHandler

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
    5) System temp dir (e.g., /tmp/kri-local-rag-logs)
    """
    # Securely create a temporary directory as a fallback
    fallback_dir = Path(tempfile.gettempdir()) / "kri-local-rag-logs"

    candidate_strings = [
        os.getenv("APP_LOG_DIR"),
        os.getenv("LOG_DIR"),
        "/app/logs",
        str(Path.cwd() / "logs"),
        str(fallback_dir),
    ]

    for candidate in candidate_strings:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        try:
            candidate_path.mkdir(parents=True, exist_ok=True)
            # Check if the directory is writable
            test_file = candidate_path / ".writable_test"
            test_file.touch()
            test_file.unlink()
            return candidate_path
        except (PermissionError, OSError):
            continue

    # This part should ideally not be reached if the temp dir is writable,
    # but it's a safeguard.
    try:
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir
    except (PermissionError, OSError) as e:
        # If even the temp dir isn't writable, something is seriously wrong.
        # Log to stderr as a last resort.
        import sys

        print(f"FATAL: Could not create any log directory. Error: {e}", file=sys.stderr)  # noqa: T201
        # Exit or raise, as logging is critical and non-functional.
        raise SystemExit(1) from e


def _setup_logging():
    """Configure the root logger. This should only be called once."""
    global _logging_configured
    if _logging_configured:
        return

    log_dir = _resolve_log_dir()
    log_file = log_dir / "rag_system.log"

    # Use a timed rotating file handler for full-fidelity DEBUG logs
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=7,
        utc=True,
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(logging.DEBUG)  # Capture all debug messages in the file

    # Use a rich handler for user-facing console output (message-only)
    console_handler = RichHandler(
        show_time=False,
        show_path=False,
        rich_tracebacks=True,
        show_level=True,
        log_time_format="[%X]",
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(LOG_LEVEL)  # Respect user-configured level

    # Configure the root logger to capture everything; handlers will filter
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
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
    # Common PDF parsing noise (e.g., from pypdf) that doesn't affect outcomes
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    logging.getLogger("pypdf.generic._base").setLevel(logging.ERROR)

    # Capture warnings issued by the warnings module (e.g., from library deprecations)
    logging.captureWarnings(True)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified module name.
    Initializes logging on first call.
    """
    if not _logging_configured:
        _setup_logging()
    return logging.getLogger(name)


def set_log_level(level: str | None) -> None:
    """
    Set the log level for the root logger and console handler.
    This function allows CLI tools to adjust verbosity dynamically.

    Args:
        level: The log level to set. Can be 'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'.
               If None, empty, or invalid, defaults to 'INFO'.

    Examples:
        >>> set_log_level('DEBUG')  # Set to debug level
        >>> set_log_level('WARNING')  # Set to warning level
        >>> set_log_level(None)  # Default to INFO
    """
    if not _logging_configured:
        _setup_logging()

    # Input validation
    if level is None or not isinstance(level, str) or not level.strip():
        level = "INFO"
    else:
        level = level.strip().upper()

    try:
        log_level = getattr(logging, level)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Find the console handler and set its level explicitly
        for handler in root_logger.handlers:
            if isinstance(handler, RichHandler):
                handler.setLevel(log_level)
                break

        # Log the change using the configured logger
        logger = get_logger(__name__)
        logger.debug("Log level set to %s", level)

    except (ValueError, AttributeError):
        # Use the configured logger for error reporting
        logger = get_logger(__name__)
        logger.warning("Invalid log level '%s'. Defaulting to INFO.", level)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)


# --- End Logging Configuration ---


COLLECTION_NAME = os.getenv("COLLECTION_NAME", "Document")

# Text splitting parameters
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Hybrid search parameters
DEFAULT_HYBRID_ALPHA = 0.5  # 0 → pure BM25, 1 → pure vector

# Model names (single source of truth)
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_OLLAMA_MODEL = "cas/mistral-7b-instruct-v0.3"

# Model paths and caching
EMBED_MODEL_PATH = os.getenv("EMBED_MODEL_PATH", "/app/models/emb")
RERANK_MODEL_PATH = os.getenv("RERANK_MODEL_PATH", "/app/models/rerank")
HF_CACHE_DIR = os.getenv("HF_HOME", "/data/hf")

# Working model names (with environment variable overrides)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
RERANKER_MODEL = os.getenv("RERANK_MODEL", DEFAULT_RERANKER_MODEL)

# Model repository and revision configuration
EMBED_COMMIT = os.getenv("EMBED_COMMIT")
RERANK_COMMIT = os.getenv("RERANK_COMMIT")

# Offline mode configuration
# Parse TRANSFORMERS_OFFLINE environment variable properly
# "1", "true", "yes" (case-insensitive) → True (offline mode enabled)
# "0", "false", "no", empty, or not set → False (offline mode disabled)
transformers_offline_env = os.getenv("TRANSFORMERS_OFFLINE", "").lower()
TRANSFORMERS_OFFLINE = transformers_offline_env in ("1", "true", "yes")

# Ollama LLM settings (used by qa_loop.py)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
# Default to local Ollama endpoint but allow override via env variable.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")

# Weaviate batching settings (tune for performance)
# Larger batches can be faster but use more memory.
WEAVIATE_BATCH_SIZE = int(os.getenv("WEAVIATE_BATCH_SIZE", 100))
# Concurrent requests can speed up ingestion on multi-core machines.
WEAVIATE_CONCURRENT_REQUESTS = int(os.getenv("WEAVIATE_CONCURRENT_REQUESTS", 2))


# Default context window (max tokens) for Ollama LLM requests
OLLAMA_CONTEXT_TOKENS = int(os.getenv("OLLAMA_CONTEXT_TOKENS", 8192))  # e.g. 4096, 8192, etc.


# (base) PS C:\Users\PC> ollama show cas/mistral-7b-instruct-v0.3
#  Model
#    architecture        llama3
#    context length      32768
#    embedding length    4096
#    quantization        Q4_K_M
