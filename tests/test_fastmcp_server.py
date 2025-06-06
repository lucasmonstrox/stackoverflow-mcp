"""
Tests for FastMcp StackOverflow MCP server.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.fastmcp_server import (
    StackOverflowServer, 
    search_questions,
    search_by_tags,
    get_question,
    get_rate_limit_status,
    server_status,
    create_app
)


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return ServerConfig(
        host="localhost",
        port=3000,
        log_level="INFO",
        stackoverflow_api_key="test_key"
    )


@pytest.fixture
def mock_stackoverflow_client():
    """Create a mock StackOverflow client."""
    client = AsyncMock()
    client.search_questions.return_value = {
        "success": True,
        "total": 2,
        "questions": [
            {"question_id": 123, "title": "Test Question 1"},
            {"question_id": 456, "title": "Test Question 2"}
        ]
    }
    client.search_by_tags.return_value = {
        "success": True,
        "total": 1,
        "questions": [
            {"question_id": 789, "title": "Python Question"}
        ]
    }
    client.get_question_details.return_value = {
        "success": True,
        "question_id": 123,
        "title": "Test Question",
        "body": "Test body",
        "answers": []
    }
    client.get_rate_limit_status.return_value = {
        "quota_remaining": 100,
        "quota_max": 300
    }
    client.get_authentication_status.return_value = {
        "authenticated": True,
        "api_key_valid": True
    }
    client.get_queue_status.return_value = {
        "queue_size": 0,
        "processing": 0
    }
    return client


class TestStackOverflowServer:
    """Test StackOverflow server class."""
    
    def test_init(self, mock_config):
        """Test server initialization."""
        server = StackOverflowServer(mock_config)
        assert server.config == mock_config
        assert server.client is None
    
    @pytest.mark.asyncio
    async def test_initialize(self, mock_config):
        """Test server client initialization."""
        server = StackOverflowServer(mock_config)
        
        with patch('stackoverflow_mcp.fastmcp_server.StackOverflowClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            await server.initialize()
            
            assert server.client is not None
            mock_client.__aenter__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mock_config, mock_stackoverflow_client):
        """Test server cleanup."""
        server = StackOverflowServer(mock_config)
        server.client = mock_stackoverflow_client
        
        await server.cleanup()
        
        mock_stackoverflow_client.__aexit__.assert_called_once_with(None, None, None)


class TestFastMcpTools:
    """Test FastMcp tool functions."""
    
    @pytest.mark.asyncio
    async def test_search_questions(self, mock_stackoverflow_client):
        """Test search_questions tool."""
        with patch('stackoverflow_mcp.fastmcp_server.server') as mock_server:
            mock_server.initialize = AsyncMock()
            mock_server.client = mock_stackoverflow_client
            
            result = await search_questions("python async", limit=5, page=1, sort="relevance")
            
            assert result["success"] is True
            assert result["total"] == 2
            assert len(result["questions"]) == 2
            mock_stackoverflow_client.search_questions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_by_tags(self, mock_stackoverflow_client):
        """Test search_by_tags tool."""
        with patch('stackoverflow_mcp.fastmcp_server.server') as mock_server:
            mock_server.initialize = AsyncMock()
            mock_server.client = mock_stackoverflow_client
            
            result = await search_by_tags(["python", "async"], limit=10)
            
            assert result["success"] is True
            assert result["total"] == 1
            mock_stackoverflow_client.search_by_tags.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_question(self, mock_stackoverflow_client):
        """Test get_question tool."""
        with patch('stackoverflow_mcp.fastmcp_server.server') as mock_server:
            mock_server.initialize = AsyncMock()
            mock_server.client = mock_stackoverflow_client
            
            result = await get_question(123, include_answers=True)
            
            assert result["success"] is True
            assert result["question_id"] == 123
            mock_stackoverflow_client.get_question_details.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, mock_stackoverflow_client):
        """Test get_rate_limit_status tool."""
        with patch('stackoverflow_mcp.fastmcp_server.server') as mock_server:
            mock_server.initialize = AsyncMock()
            mock_server.client = mock_stackoverflow_client
            
            result = await get_rate_limit_status()
            
            assert "quota_remaining" in result
            assert result["quota_remaining"] == 100
            mock_stackoverflow_client.get_rate_limit_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_server_status_resource(self, mock_stackoverflow_client):
        """Test server_status resource."""
        with patch('stackoverflow_mcp.fastmcp_server.server') as mock_server:
            mock_server.initialize = AsyncMock()
            mock_server.client = mock_stackoverflow_client
            mock_server.config = ServerConfig()
            
            resource = await server_status()
            
            assert resource.uri == "stackoverflow://status"
            assert resource.name == "Server Status"
            assert "server" in resource.text
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in tools."""
        with patch('stackoverflow_mcp.fastmcp_server.server') as mock_server:
            mock_server.initialize = AsyncMock()
            mock_server.client = None  # Simulate client error
            
            result = await search_questions("test")
            
            assert "error" in result
            assert result["success"] is False


class TestFastMcpApp:
    """Test FastMcp app creation."""
    
    def test_create_app(self, mock_config):
        """Test app creation."""
        app = create_app(mock_config)
        
        # Check that app is a FastMCP instance
        from fastmcp import FastMCP
        assert isinstance(app, FastMCP)
        assert app.name == "StackOverflow MCP Server"
    
    def test_app_has_tools(self, mock_config):
        """Test that app has expected tools."""
        app = create_app(mock_config)
        
        # Get tool names
        tools = app.get_tools()
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "search_questions",
            "search_by_tags", 
            "get_question",
            "get_question_with_answers",
            "get_rate_limit_status",
            "get_authentication_status",
            "get_queue_status"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    def test_app_has_resources(self, mock_config):
        """Test that app has expected resources."""
        app = create_app(mock_config)
        
        # Get resource URIs
        resources = app.get_resources()
        resource_uris = [resource.uri for resource in resources]
        
        assert "stackoverflow://status" in resource_uris


if __name__ == "__main__":
    pytest.main([__file__]) 