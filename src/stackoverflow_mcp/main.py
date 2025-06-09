"""
Main entry point for StackOverflow MCP server with enhanced CLI and deployment features.
"""

import asyncio
import os
import signal
import socket
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import click
from .config import ServerConfig
from .logging import setup_logging, get_logger
from .server import StackOverflowMCPServer


logger = get_logger("main")


class ServerManager:
    """Enhanced server manager with automatic configuration and graceful shutdown."""
    
    def __init__(self):
        self.server: Optional[StackOverflowMCPServer] = None
        self.shutdown_event = asyncio.Event()
        self._original_sigint_handler = None
        self._original_sigterm_handler = None
    
    def find_available_port(self, start_port: int = 3000, max_attempts: int = 100) -> int:
        """Find an available port starting from the given port."""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    logger.debug(f"Port {port} is available")
                    return port
            except socket.error:
                logger.debug(f"Port {port} is in use")
                continue
        
        raise RuntimeError(f"No available ports found in range {start_port}-{start_port + max_attempts}")
    
    def discover_config_file(self, working_dir: Path) -> Optional[Path]:
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
    
    def detect_working_directory(self) -> Path:
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
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self.shutdown())
            else:
                self.shutdown_event.set()
        
        # Store original handlers
        self._original_sigint_handler = signal.signal(signal.SIGINT, signal_handler)
        self._original_sigterm_handler = signal.signal(signal.SIGTERM, signal_handler)
    
    def restore_signal_handlers(self):
        """Restore original signal handlers."""
        if self._original_sigint_handler:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
        if self._original_sigterm_handler:
            signal.signal(signal.SIGTERM, self._original_sigterm_handler)
    
    async def shutdown(self):
        """Gracefully shutdown the server."""
        logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()
        
        if self.server:
            try:
                await self.server.stop()
                logger.info("Server stopped successfully")
            except Exception as e:
                logger.error(f"Error during server shutdown: {e}")
    
    async def start_server(self, config: ServerConfig) -> int:
        """Start the server with enhanced monitoring and health checks."""
        try:
            # Create server instance
            self.server = StackOverflowMCPServer(config)
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            logger.info("=" * 60)
            logger.info("StackOverflow MCP Server Starting")
            logger.info("=" * 60)
            logger.info(f"Host: {config.host}")
            logger.info(f"Port: {config.port}")
            logger.info(f"Working Directory: {Path.cwd()}")
            logger.info(f"Log Level: {config.log_level}")
            logger.info(f"API Key Configured: {'Yes' if config.stackoverflow_api_key else 'No'}")
            logger.info("=" * 60)
            
            # Start server
            server_task = asyncio.create_task(self.server.start())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel server task
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return 1
        finally:
            self.restore_signal_handlers()


@click.command()
@click.option(
    "--host", 
    default="localhost", 
    help="Host to bind the server to"
)
@click.option(
    "--port", 
    default=None, 
    type=int, 
    help="Port to bind the server to (auto-detect if not specified)"
)
@click.option(
    "--log-level", 
    default="INFO", 
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level"
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to configuration file (auto-discover if not specified)"
)
@click.option(
    "--working-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Working directory (auto-detect if not specified)"
)
@click.option(
    "--auto-port/--no-auto-port",
    default=True,
    help="Automatically find an available port if specified port is in use"
)
@click.option(
    "--dev/--prod",
    default=False,
    help="Run in development mode (more verbose logging, auto-reload)"
)
@click.option(
    "--health-check/--no-health-check",
    default=True,
    help="Enable startup health checks"
)
@click.version_option(version="0.1.0", prog_name="stackoverflow-mcp")
def main(
    host: str, 
    port: Optional[int], 
    log_level: str, 
    config_file: Optional[str],
    working_dir: Optional[str],
    auto_port: bool,
    dev: bool,
    health_check: bool
) -> None:
    """
    StackOverflow MCP Server - Enhanced CLI with auto-configuration.
    
    This command starts a Model Context Protocol (MCP) server that provides
    access to StackOverflow's API for searching questions, getting question
    details, and browsing by tags.
    
    The server automatically detects:
    - Working directory and project structure
    - Configuration files (.stackoverflow-mcp.json, etc.)
    - Available ports if auto-port is enabled
    
    Examples:
    
      # Start with auto-detection
      stackoverflow-mcp
      
      # Start on specific port
      stackoverflow-mcp --port 8080
      
      # Start with custom config
      stackoverflow-mcp --config-file ./my-config.json
      
      # Development mode with debug logging
      stackoverflow-mcp --dev --log-level DEBUG
    """
    
    # Create server manager
    manager = ServerManager()
    
    try:
        # 1. Detect working directory
        if working_dir:
            work_dir = Path(working_dir)
        else:
            work_dir = manager.detect_working_directory()
        
        # Change to working directory
        try:
            os.chdir(work_dir)
            logger.debug(f"Changed working directory to: {work_dir}")
        except Exception as e:
            logger.warning(f"Failed to change to working directory {work_dir}: {e}")
            work_dir = Path.cwd()  # Use current directory as fallback
        
        # 2. Discover configuration file
        if not config_file:
            discovered_config = manager.discover_config_file(work_dir)
            if discovered_config:
                config_file = str(discovered_config)
        
        # 3. Load configuration
        config = ServerConfig.load_from_env()
        
        # Load from config file if specified
        if config_file:
            logger.info(f"Loading configuration from: {config_file}")
            try:
                import json
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    # Update config with file data
                    for key, value in config_data.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                logger.info("Configuration loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
        
        # 4. Override with command line arguments
        if host != "localhost":
            config.host = host
        if log_level != "INFO":
            config.log_level = log_level
        
        # Development mode adjustments
        if dev:
            if config.log_level == "INFO":
                config.log_level = "DEBUG"
            logger.info("Development mode enabled")
        
        # 5. Setup logging first
        setup_logging(config.log_level)
        
        # 6. Handle port configuration
        if port is not None:
            if auto_port:
                try:
                    # Test if the specified port is available
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('', port))
                    config.port = port
                except socket.error:
                    logger.warning(f"Port {port} is in use, finding alternative...")
                    config.port = manager.find_available_port(port)
                    logger.info(f"Using port {config.port} instead")
            else:
                config.port = port
        else:
            # Auto-select port starting from default
            config.port = manager.find_available_port(config.port if hasattr(config, 'port') else 3000)
        
        # 7. Validate configuration
        if health_check:
            logger.info("Performing startup health checks...")
            
            # Check required dependencies
            missing_deps = []
            try:
                import httpx
                import mcp
            except ImportError as e:
                missing_deps.append(str(e))
            
            if missing_deps:
                logger.error("Missing required dependencies:")
                for dep in missing_deps:
                    logger.error(f"  - {dep}")
                logger.error("Please install missing dependencies with: pip install -e .")
                return
            
            logger.info("Health checks passed")
        
        # 8. Start server
        logger.info(f"Starting server in {'development' if dev else 'production'} mode...")
        exit_code = asyncio.run(manager.start_server(config))
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Startup error: {e}")
        if dev:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 