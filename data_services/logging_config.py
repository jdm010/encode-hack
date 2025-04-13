"""Logging configuration for the application.

This module sets up logging with a consistent format across all modules.
"""

import logging
import sys
from typing import Optional

def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Configure and return a logger with consistent formatting.

    Args:
        name: Name of the logger, typically __name__ of the calling module.
        level: Optional logging level, defaults to INFO if not specified.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # Only add handler if logger doesn't already have one
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(level or logging.INFO)
    return logger
