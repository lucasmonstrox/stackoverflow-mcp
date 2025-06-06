"""
Tests for the basic MCP server framework.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.server import StackOverflowMCPServer
from stackoverflow_mcp.logging import setup_logging


class TestServerConfig:
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ServerConfig()
        assert config.host == "localhost"
        assert config.port == 3000
        assert config.stackoverflow_api_key is None
        assert config.max_requests_per_minute == 30
        
    def test_load_from_env(self):
        """Test loading configuration from environment."""
        with patch.dict('os.environ', {
            'MCP_HOST': 'test-host',
            'MCP_PORT': '4000',
            'STACKOVERFLOW_API_KEY': 'test-key'
        }):
            config = ServerConfig.load_from_env()
            assert config.host == "test-host"
            assert config.port == 4000
            assert config.stackoverflow_api_key == "test-key"


class TestStackOverflowMCPServer:
    """Test MCP server functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ServerConfig(host="localhost", port=3001)
    
    @pytest.fixture
    def server(self, config):
        """Create test server instance."""
        return StackOverflowMCPServer(config)
    
    def test_server_initialization(self, server, config):
        """Test server initialization."""
        assert server.config == config
        assert server.server.name == "stackoverflow-mcp"
        assert server._shutdown_event is not None
    
    def test_server_has_handlers(self, server):
        """Test that server has the required handlers configured."""
        # Check that handlers are registered
        assert hasattr(server.server, 'list_tools')
        assert hasattr(server.server, 'list_resources')
        assert hasattr(server.server, 'call_tool')
        assert hasattr(server.server, 'read_resource')
    
    def test_config_validation(self, config):
        """Test configuration validation."""
        assert config.host
        assert config.port > 0
        assert config.max_requests_per_minute > 0
        assert config.max_content_length > 0


class TestLogging:
    """Test logging configuration."""
    
    def test_setup_logging(self):
        """Test logging setup."""
        setup_logging("DEBUG")
        
        import logging
        logger = logging.getLogger("stackoverflow_mcp")
        assert logger.level == logging.DEBUG
        
    def test_get_logger(self):
        """Test logger creation."""
        from stackoverflow_mcp.logging import get_logger
        logger = get_logger("test")
        assert logger.name == "stackoverflow_mcp.test"


class TestIntegration:
    """Integration tests for the basic framework."""
    
    def test_server_creation_and_shutdown_signal(self):
        """Test server creation and shutdown event."""
        config = ServerConfig()
        server = StackOverflowMCPServer(config)
        
        # Test shutdown event
        assert not server._shutdown_event.is_set()
        
        # Simulate shutdown
        server._shutdown_event.set()
        assert server._shutdown_event.is_set()
    
    def test_basic_workflow(self):
        """Test basic server workflow without actual networking."""
        config = ServerConfig.load_from_env()
        server = StackOverflowMCPServer(config)
        
        # Server should be properly initialized
        assert server.server.name == "stackoverflow-mcp"
        assert server.config.host
        assert server.config.port > 0 