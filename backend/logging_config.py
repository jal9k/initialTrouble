"""Logging configuration for Network Diagnostics."""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Path | None = None,
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to also log to a file
        log_dir: Directory for log files (default: data/logs/)

    Returns:
        Configured root logger
    """
    # Create logger
    logger = logging.getLogger("network_diag")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stderr to not interfere with Rich output)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        log_dir = log_dir or Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Daily log file
        log_file = log_dir / f"network_diag_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # All levels to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_file}")

    return logger


def get_logger(name: str = "network_diag") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)

