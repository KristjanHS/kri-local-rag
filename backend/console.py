"""Console and logging setup for the application."""

import logging
from logging import Logger

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def get_logger(name: str) -> Logger:
    """Get a logger with a rich handler."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(show_time=False, show_path=False, rich_tracebacks=True)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
