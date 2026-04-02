"""
Logger - Logging configuration for Bgpt.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Global logger instance
_logger: Optional[logging.Logger] = None

def setup_logger(name: str = "bgpt", level: str = "INFO") -> logging.Logger:
    """Setup main logger."""
    global _logger

    if _logger is not None:
        return _logger

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    
    if not logger.handlers:
        # Remove console handler entirely - no console logging
        # All logging goes to file only
        
        # File handler only
        try:
            log_dir = Path.home() / ".bgpt" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_dir / "bgpt.log")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception:
            # If file logging fails, create a null handler
            null_handler = logging.NullHandler()
            logger.addHandler(null_handler)

    _logger = logger
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get logger for module."""
    # Ensure main logger is initialized
    if _logger is None:
        setup_logger()
    return logging.getLogger(f"bgpt.{name}")
