"""
Logging configuration for all agents
"""
import logging
import os

def setup_logging(name: str = None) -> logging.Logger:
    """Set up logging with consistent format"""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(name if name else __name__)