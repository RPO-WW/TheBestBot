"""Centralized logging configuration for the project."""
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format and StreamHandler.

    Args:
        level: Logging level for the root logger.
    """
    root = logging.getLogger()
    # Avoid adding multiple handlers if setup_logging is called more than once
    if root.handlers:
        return

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    root.setLevel(level)
    root.addHandler(handler)


__all__ = ["setup_logging"]
