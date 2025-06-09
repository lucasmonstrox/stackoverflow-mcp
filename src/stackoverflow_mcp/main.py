"""
Simplified main entry point for StackOverflow MCP server using FastMcp.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import click

from .config import ServerConfig
from .logging import setup_logging, get_logger
from .server import run_server, create_app

logger = get_logger("fastmcp_main")


def discover_config_file(working_dir: Path) -> Optional[Path]:
    """
    Automatically discover configuration files in the working directory hierarchy.
    
    Searches for config files in the following order:
    1. .stackoverflow-mcp.json
    2. stackoverflow-mcp.config.json
    3. config/stackoverflow-mcp.json
    4. .config/stackoverflow-mcp.json
    """
    config_names = [
        ".stackoverflow-mcp.json",
        "stackoverflow-mcp.config.json", 
        "config/stackoverflow-mcp.json",
        ".config/stackoverflow-mcp.json"
    ]
    
    # Search current directory and parent directories
    current_dir = working_dir
    while current_dir != current_dir.parent:  # Stop at filesystem root
        for config_name in config_names:
            config_path = current_dir / config_name
            if config_path.exists() and config_path.is_file():
                logger.info(f"Found configuration file: {config_path}")
                return config_path
        current_dir = current_dir.parent
    
    logger.debug("No configuration file found")
    return None


def detect_working_directory() -> Path:
    """
    Detect the appropriate working directory.
    
    Priority:
    1. Current working directory if it contains project files
    2. Directory containing the script if run directly
    3. Current working directory as fallback
    """
    cwd = Path.cwd()
    
    # Check if current directory looks like a project directory
    project_indicators = [
        "pyproject.toml", "package.json", ".git", 
        ".stackoverflow-mcp.json", "stackoverflow-mcp.config.json"
    ]
    
    for indicator in project_indicators:
        if (cwd / indicator).exists():
            logger.debug(f"Detected project directory from {indicator}: {cwd}")
            return cwd
    
    # Check parent directories for project indicators
    current = cwd
    while current != current.parent:
        for indicator in project_indicators:
            if (current / indicator).exists():
                logger.info(f"Found project directory: {current}")
                return current
        current = current.parent
    
    logger.debug(f"Using current working directory: {cwd}")
    return cwd


@click.command()
@click.option(
    "--host", 
    default="localhost", 
    help="Host to bind the server to"
)
@click.option(
    "--port", 
    default=3000, 
    type=int, 
    help="Port to bind the server to"
)
@click.option(
    "--log-level", 
    default="INFO", 
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level"
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to configuration file (auto-discover if not specified)"
)
@click.option(
    "--working-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Working directory (auto-detect if not specified)"
)
@click.option(
    "--api-key",
    help="StackOverflow API key"
)
@click.version_option(version="0.1.0", prog_name="stackoverflow-mcp-fastmcp")
def main(
    host: str, 
    port: int, 
    log_level: str, 
    config_file: Optional[str],
    working_dir: Optional[str],
    api_key: Optional[str]
) -> None:
    """
    StackOverflow MCP Server using FastMcp framework.
    
    A simplified, elegant implementation providing StackOverflow search capabilities
    through the Model Context Protocol.
    """
    
    # Determine working directory
    if working_dir:
        work_dir = Path(working_dir)
    else:
        work_dir = detect_working_directory()
    
    # Change to working directory to ensure proper config file discovery
    import os
    original_cwd = Path.cwd()
    try:
        os.chdir(work_dir)
        logger.debug(f"Changed working directory to: {work_dir}")
    except Exception as e:
        logger.warning(f"Failed to change to working directory {work_dir}: {e}")
        work_dir = original_cwd
    
    # Discover config file if not specified
    if config_file:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = work_dir / config_path
    else:
        config_path = discover_config_file(work_dir)
    
    # Create configuration
    try:
        config = ServerConfig.from_file(config_path) if config_path else ServerConfig()
        
        # Override with CLI arguments
        if host != "localhost":
            config.host = host
        if port != 3000:
            config.port = port
        if log_level != "INFO":
            config.log_level = log_level
        if api_key:
            config.stackoverflow_api_key = api_key
            
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)
    
    # Setup logging
    setup_logging(config.log_level)
    
    try:
        logger.info("=" * 60)
        logger.info("StackOverflow MCP Server (FastMcp)")
        logger.info("=" * 60)
        logger.info(f"Working Directory: {work_dir}")
        logger.info(f"Configuration File: {config_path or 'None (using defaults)'}")
        logger.info(f"Host: {config.host}")
        logger.info(f"Port: {config.port}")
        logger.info(f"Log Level: {config.log_level}")
        logger.info(f"API Key Configured: {'Yes' if config.stackoverflow_api_key else 'No'}")
        logger.info("=" * 60)
        
        # Run the server with proper asyncio handling
        try:
            asyncio.run(run_server(config))
        except RuntimeError as e:
            if "already running" in str(e).lower():
                logger.warning("AsyncIO loop already running, creating new event loop")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(run_server(config))
                finally:
                    loop.close()
            else:
                raise
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 