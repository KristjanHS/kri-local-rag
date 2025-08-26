import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from rich.logging import RichHandler

# Load environment variables from the project root .env (if present)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# --- Logging Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_logging_configured = False


def _setup_logging():
    """Configure the root logger. This should only be called once."""
    global _logging_configured
    if _logging_configured:
        return

    # Determine log level from environment
    try:
        log_level = getattr(logging, LOG_LEVEL)
    except AttributeError:
        log_level = logging.INFO

    # Console handler: Rich for TTY, plain StreamHandler otherwise
    if sys.stderr.isatty():
        console_handler = RichHandler(
            show_time=False,
            show_path=False,
            rich_tracebacks=True,
            show_level=True,
            log_time_format="[%X]",
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    console_handler.setLevel(log_level)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Optional file logging only when APP_LOG_DIR is explicitly provided
    app_log_dir = os.getenv("APP_LOG_DIR")
    if app_log_dir:
        try:
            log_dir_path = Path(app_log_dir)
            log_dir_path.mkdir(parents=True, exist_ok=True)
            # Rotating file handler: rotate at midnight, keep limited backups
            backup_count_str = os.getenv("APP_LOG_BACKUP_COUNT", "5").strip()
            try:
                backup_count = max(0, int(backup_count_str))
            except ValueError:
                backup_count = 7

            file_handler = TimedRotatingFileHandler(
                filename=log_dir_path / "rag_system.log",
                when="midnight",
                backupCount=backup_count,
                encoding="utf-8",
                utc=True,
            )
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
        except (PermissionError, OSError) as e:
            # If file logging fails, log a warning and continue with console-only logging
            logging.warning("Failed to configure file logging to '%s'. Error: %s", app_log_dir, e)

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

        # Find console-like handlers and set their level explicitly
        for handler in root_logger.handlers:
            is_console_like = isinstance(handler, (RichHandler, logging.StreamHandler))
            if is_console_like and not isinstance(handler, logging.FileHandler):
                handler.setLevel(log_level)

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


# Centralized service URL resolution with localhost fallbacks
def get_service_url(service: str) -> str:
    """Resolve service URL from environment variables with localhost fallbacks.

    Args:
        service: Either "ollama" or "weaviate".

    Returns:
        The resolved service base URL.

    Raises:
        ValueError: If an unknown service name is provided.
    """
    if service == "ollama":
        return os.getenv("OLLAMA_URL", "http://localhost:11434")
    if service == "weaviate":
        return os.getenv("WEAVIATE_URL", "http://localhost:8080")
    raise ValueError(f"Unknown service: {service}")


# Backwards-compatible constants sourced from the centralized resolver
OLLAMA_URL = get_service_url("ollama")
WEAVIATE_URL = get_service_url("weaviate")

# Weaviate batching settings (tune for performance)
# Larger batches can be faster but use more memory.
WEAVIATE_BATCH_SIZE = int(os.getenv("WEAVIATE_BATCH_SIZE", 100))
# Concurrent requests can speed up ingestion on multi-core machines.
WEAVIATE_CONCURRENT_REQUESTS = int(os.getenv("WEAVIATE_CONCURRENT_REQUESTS", 2))


# Default context window (max tokens) for Ollama LLM requests
OLLAMA_CONTEXT_TOKENS = int(os.getenv("OLLAMA_CONTEXT_TOKENS", 8192))  # e.g. 4096, 8192, etc.


def is_running_in_docker() -> bool:
    """
    Detect if the current process is running inside a Docker container.

    Uses TEST_DOCKER environment variable for explicit environment control.
    This is simpler and more testable than file-based detection.

    Returns:
        bool: True if running inside Docker, False otherwise
    """
    # Use TEST_DOCKER environment variable for explicit control
    # This is much simpler and more reliable than file-based detection
    test_docker = os.getenv("TEST_DOCKER", "false").lower()
    return test_docker == "true"


# (base) PS C:\Users\PC> ollama show cas/mistral-7b-instruct-v0.3
#  Model
#    architecture        llama3
#    context length      32768
#    embedding length    4096
#    quantization        Q4_K_M
