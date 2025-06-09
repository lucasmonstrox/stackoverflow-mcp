"""
Basic tests for FastMCP implementation.
"""

import pytest
from unittest.mock import Mock, patch
import asyncio

def test_module_imports():
    """Test that all required modules can be imported."""
    from stackoverflow_mcp.main import main
    from stackoverflow_mcp.server import run_server, create_app
    from stackoverflow_mcp.config import ServerConfig
    from stackoverflow_mcp.stackoverflow_client import StackOverflowClient
    assert main is not None
    assert run_server is not None
    assert create_app is not None
    assert ServerConfig is not None
    assert StackOverflowClient is not None

def test_server_config():
    """Test ServerConfig creation."""
    from stackoverflow_mcp.config import ServerConfig
    
    config = ServerConfig()
    assert config.host == "localhost"
    assert config.port == 3000
    assert config.log_level == "INFO"

def test_stackoverflow_client_creation():
    """Test StackOverflowClient can be created."""
    from stackoverflow_mcp.stackoverflow_client import StackOverflowClient
    from stackoverflow_mcp.config import ServerConfig
    
    config = ServerConfig()
    client = StackOverflowClient(config)
    assert client is not None

@pytest.mark.asyncio
async def test_create_app():
    """Test that FastMCP app can be created."""
    from stackoverflow_mcp.server import create_app
    from stackoverflow_mcp.config import ServerConfig
    
    config = ServerConfig()
    app = create_app(config)
    assert app is not None

def test_cli_help():
    """Test that CLI help works."""
    from click.testing import CliRunner
    from stackoverflow_mcp.main import main
    
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert "StackOverflow MCP Server" in result.output 