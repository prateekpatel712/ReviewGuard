"""
ReviewGuard — Core Logging module.
Configures and exposes a unified logging instance.
"""

import logging
import os


def setup_logger() -> logging.Logger:
    """
    Initialises the master logger for ReviewGuard.
    Writes INFO logs to the console and to logs/review_guard.log.

    Returns:
        logging.Logger: The configured logger instance.
    """
    os.makedirs("logs", exist_ok=True)
    
    logger = logging.getLogger("ReviewGuard")
    
    # Only assign handlers if not already bound
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        # File output
        file_handler = logging.FileHandler("logs/review_guard.log", mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Standard output
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
    return logger


logger = setup_logger()
