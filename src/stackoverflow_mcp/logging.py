"""
Logging configuration for StackOverflow MCP server.
"""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", format_string: Optional[str] = None) -> None:
    """Setup logging configuration for the MCP server."""
    
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        stream=sys.stdout,
        force=True
    )
    
    # Set specific loggers
    logger = logging.getLogger("stackoverflow_mcp")
    logger.setLevel(numeric_level)
    
    # Reduce noise from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"stackoverflow_mcp.{name}") 