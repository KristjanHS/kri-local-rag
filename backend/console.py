"""Console and logging setup for the application."""

from logging import Logger

from rich.console import Console

from backend.config import get_logger as get_root_logger

console = Console()


def get_logger(name: str) -> Logger:
    """Get a logger that delegates to the centralized root logger."""
    return get_root_logger(name)
