"""
Simplified main entry point for StackOverflow MCP server using FastMcp.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import click

from .config import ServerConfig
from .logging import setup_logging, get_logger, disable_all_logging_for_mcp_mode
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
    "--log-level", 
    default="WARNING",  # Changed from INFO to WARNING to reduce noise
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
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
@click.version_option(version="0.2.2", prog_name="stackoverflow-mcp-fastmcp")
def main(
    log_level: str, 
    config_file: Optional[str],
    working_dir: Optional[str],
    api_key: Optional[str]
) -> None:
    """
    StackOverflow MCP Server using FastMcp framework.
    
    A simplified, elegant implementation providing StackOverflow search capabilities
    through the Model Context Protocol (stdio mode only).
    """
    
    # Detect if we're running in MCP mode (which is always the case now)
    # For MCP protocol, completely disable logging to avoid stdout pollution
    is_mcp_mode = True
    
    if is_mcp_mode:
        # Nuclear option: completely disable all logging for MCP mode
        disable_all_logging_for_mcp_mode()
    else:
        # Setup minimal logging for MCP mode
        actual_log_level = "ERROR" if log_level in ["DEBUG", "INFO", "WARNING"] else log_level
        setup_logging(actual_log_level)
    
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
    except Exception:
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
        
        # Override with CLI arguments - force ERROR level for MCP mode
        config.log_level = "CRITICAL" if is_mcp_mode else log_level
        if api_key:
            config.stackoverflow_api_key = api_key
            
    except Exception as e:
        if not is_mcp_mode:
            click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)
    
    try:
        # Run the server with proper asyncio handling
        try:
            asyncio.run(run_server(config))
        except RuntimeError as e:
            if "already running" in str(e).lower():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(run_server(config))
                finally:
                    loop.close()
            else:
                raise
        
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        if not is_mcp_mode:
            # Only show errors in non-MCP mode
            logger = get_logger("fastmcp_main")
            logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 