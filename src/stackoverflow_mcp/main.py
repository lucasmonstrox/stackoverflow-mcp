"""
Simplified main entry point for StackOverflow MCP server using FastMcp.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional
import click

from . import __version__
from .config import ServerConfig
from .logging import disable_all_logging_for_mcp_mode
from .server import run_server

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
                return config_path
        current_dir = current_dir.parent
    
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
            return cwd
    
    # Check parent directories for project indicators
    current = cwd
    while current != current.parent:
        for indicator in project_indicators:
            if (current / indicator).exists():
                return current
        current = current.parent
    
    return cwd


@click.command()
@click.option(
    "--working-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Working directory (auto-detect if not specified)"
)
@click.option(
    "--api-key",
    help="StackOverflow API key"
)
@click.version_option(version=__version__, prog_name="stackoverflow-mcp-fastmcp")
def main(
    working_dir: Optional[str],
    api_key: Optional[str]
) -> None:
    """
    StackOverflow MCP Server using FastMcp framework.
    
    A simplified, elegant implementation providing StackOverflow search capabilities
    through the Model Context Protocol (stdio mode only).
    """
    
    # Disable all logging for MCP mode to avoid stdout pollution
    disable_all_logging_for_mcp_mode()
    
    # Determine working directory
    if working_dir:
        work_dir = Path(working_dir)
    else:
        work_dir = detect_working_directory()
    
    # Change to working directory
    original_cwd = Path.cwd()
    try:
        os.chdir(work_dir)
    except Exception:
        work_dir = original_cwd
    
    # Discover config file and create configuration
    try:
        config_path = discover_config_file(work_dir)
        config = ServerConfig.from_file(config_path) if config_path else ServerConfig()
        
        # Set critical log level for MCP mode
        config.log_level = "CRITICAL"
        
        # Override with CLI arguments
        if api_key:
            config.stackoverflow_api_key = api_key
            
    except Exception:
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
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main() 