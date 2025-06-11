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
    
    # Configure root logger - CRITICAL: use stderr to avoid polluting stdout for MCP
    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        stream=sys.stderr,  # Changed from sys.stdout to sys.stderr
        force=True
    )
    
    # Set specific loggers
    logger = logging.getLogger("stackoverflow_mcp")
    logger.setLevel(numeric_level)
    
    # Reduce noise from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # CRITICAL: Disable FastMCP internal logging to prevent stdout pollution
    # FastMCP creates its own loggers that can pollute stdout in MCP mode
    fastmcp_loggers = [
        "fastmcp",
        "FastMCP",
        "fastmcp.server",
        "fastmcp.server.server",
        "FastMCP.fastmcp.server.server",
        "fastmcp.fastmcp.server.server",
        "mcp",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error"
    ]
    
    for logger_name in fastmcp_loggers:
        fastmcp_logger = logging.getLogger(logger_name)
        fastmcp_logger.setLevel(logging.CRITICAL)  # Only show critical errors
        fastmcp_logger.propagate = False  # Don't propagate to parent loggers


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"stackoverflow_mcp.{name}")


def disable_all_logging_for_mcp_mode() -> None:
    """
    Completely disable all logging output for MCP mode.
    This is the nuclear option to ensure zero stdout pollution.
    """
    # Disable root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL + 1)  # Above CRITICAL
    
    # Remove all handlers from root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Disable specific loggers
    loggers_to_silence = [
        "fastmcp",
        "FastMCP", 
        "fastmcp.server",
        "fastmcp.server.server",
        "FastMCP.fastmcp.server.server",
        "fastmcp.fastmcp.server.server",
        "mcp",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "stackoverflow_mcp"
    ]
    
    for logger_name in loggers_to_silence:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL + 1)  # Above CRITICAL
        logger.propagate = False
        # Remove all handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler) 