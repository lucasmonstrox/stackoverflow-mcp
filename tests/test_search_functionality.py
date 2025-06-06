"""
Tests for StackOverflow search functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.stackoverflow_client import StackOverflowClient
from stackoverflow_mcp.server import StackOverflowMCPServer


class TestStackOverflowClient:
    """Test StackOverflow API client."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ServerConfig(
            stackoverflow_api_key="test-key",
            max_requests_per_minute=60,
            retry_delay=0.1
        )
    
    @pytest.fixture
    def client(self, config):
        """Create test client."""
        return StackOverflowClient(config)
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client, config):
        """Test client initialization."""
        assert client.config == config
        assert client.base_url == config.stackoverflow_base_url
        assert client.api_key == config.stackoverflow_api_key
        assert client.session is not None
    
    @pytest.mark.asyncio
    async def test_search_questions_validation(self, client):
        """Test search parameter validation."""
        # Test empty query
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await client.search_questions("")
        
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await client.search_questions("   ")
    
    @pytest.mark.asyncio
    async def test_search_questions_success(self, client):
        """Test successful search."""
        mock_response = {
            "items": [
                {
                    "question_id": 123,
                    "title": "Test Question",
                    "score": 10,
                    "view_count": 100,
                    "answer_count": 2,
                    "tags": ["python", "testing"],
                    "link": "https://stackoverflow.com/questions/123"
                }
            ],
            "total": 1,
            "has_more": False
        }
        
        with patch.object(client, '_make_raw_request', return_value=mock_response) as mock_request:
            result = await client.search_questions("python testing")
            
            assert result["total"] == 1
            assert len(result["items"]) == 1
            assert result["items"][0]["question_id"] == 123
            
            # Verify API call was made with correct parameters
            mock_request.assert_called()
            args, kwargs = mock_request.call_args
            endpoint, params, use_auth = args
            assert endpoint == "search/advanced"
            assert params["intitle"] == "python testing"
    
    @pytest.mark.asyncio
    async def test_get_question_details_success(self, client):
        """Test getting question details."""
        mock_question_response = {
            "items": [
                {
                    "question_id": 123,
                    "title": "Test Question",
                    "body": "<p>Test body</p>",
                    "score": 10,
                    "view_count": 100,
                    "answer_count": 2,
                    "tags": ["python"],
                    "link": "https://stackoverflow.com/questions/123"
                }
            ]
        }
        
        mock_answers_response = {
            "items": [
                {"answer_id": 456, "score": 15, "is_accepted": True}
            ]
        }
        
        with patch.object(client, '_make_raw_request', side_effect=[mock_question_response, mock_answers_response]) as mock_request:
            result = await client.get_question_details(123, include_answers=True)
            
            assert result["question_id"] == 123
            assert result["title"] == "Test Question"
            assert "answers" in result
            assert len(result["answers"]) == 1
            
            # Should have called for question details and answers
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_question_details_not_found(self, client):
        """Test getting details for non-existent question."""
        mock_response = {"items": []}
        
        with patch.object(client, '_make_raw_request', return_value=mock_response):
            with pytest.raises(Exception, match="Question 123 not found"):
                await client.get_question_details(123)

    @pytest.mark.asyncio
    async def test_search_by_tags_success(self, client):
        """Test successful tag search."""
        mock_response = {
            "items": [
                {
                    "question_id": 456,
                    "title": "Python async/await question",
                    "score": 25,
                    "view_count": 300,
                    "answer_count": 3,
                    "tags": ["python", "async-await"],
                    "link": "https://stackoverflow.com/questions/456"
                }
            ],
            "total": 1,
            "has_more": False
        }
        
        with patch.object(client, '_make_raw_request', return_value=mock_response) as mock_request:
            result = await client.search_by_tags(["python", "async"])
            
            assert result == mock_response
            # Verify API call was made with correct parameters including use_auth parameter
            mock_request.assert_called_once_with("search/advanced", {
                "tagged": "python;async",
                "page": 1,
                "pagesize": 10,
                "sort": "activity",
                "order": "desc",
                "filter": "default"
            }, False)  # use_auth parameter

    @pytest.mark.asyncio
    async def test_search_by_tags_validation(self, client):
        """Test tag search parameter validation."""
        # Test empty tags
        with pytest.raises(ValueError, match="At least one tag is required"):
            await client.search_by_tags([])
        
        with pytest.raises(ValueError, match="At least one tag is required"):
            await client.search_by_tags(["", "  "])


class TestStackOverflowMCPServerSearch:
    """Test MCP server search functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ServerConfig()
    
    @pytest.fixture
    def server(self, config):
        """Create test server."""
        return StackOverflowMCPServer(config)
    
    @pytest.mark.asyncio
    async def test_search_questions_tool_empty_query(self, server):
        """Test search tool with empty query."""
        result = await server._handle_search_questions({"query": ""})
        
        assert "content" in result
        assert "Error: Search query cannot be empty" in result["content"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_search_questions_tool_success(self, server):
        """Test successful search tool call."""
        mock_client = AsyncMock()
        mock_client.search_questions.return_value = {
            "items": [
                {
                    "question_id": 123,
                    "title": "How to test Python code?",
                    "score": 15,
                    "view_count": 500,
                    "answer_count": 3,
                    "tags": ["python", "testing"],
                    "link": "https://stackoverflow.com/questions/123"
                }
            ],
            "total": 1
        }
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_search_questions({
            "query": "python testing",
            "limit": 10,
            "page": 1,
            "sort": "relevance"
        })
        
        assert "content" in result
        content = result["content"][0]["text"]
        assert "Found 1 questions for 'python testing'" in content
        assert "How to test Python code?" in content
        assert "ID: 123" in content
        assert "Score: 15" in content
        
        mock_client.search_questions.assert_called_once_with(
            query="python testing",
            page=1,
            page_size=10,
            sort="relevance"
        )
    
    @pytest.mark.asyncio
    async def test_search_questions_tool_no_results(self, server):
        """Test search tool with no results."""
        mock_client = AsyncMock()
        mock_client.search_questions.return_value = {
            "items": [],
            "total": 0
        }
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_search_questions({"query": "nonexistent"})
        
        assert "content" in result
        assert "No questions found for query: 'nonexistent'" in result["content"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_get_question_tool_success(self, server):
        """Test get question tool success."""
        mock_client = AsyncMock()
        mock_client.get_question_details.return_value = {
            "question_id": 123,
            "title": "Test Question",
            "body": "<p>Test body content</p>",
            "score": 10,
            "view_count": 100,
            "answer_count": 2,
            "tags": ["python"],
            "link": "https://stackoverflow.com/questions/123"
        }
        # Mock as regular method, not async
        mock_client._convert_html_to_markdown = MagicMock(return_value="Test body content")
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_get_question({"question_id": 123})
        
        assert "content" in result
        content = result["content"][0]["text"]
        assert "Test Question" in content
        assert "ID: 123" in content
        assert "Score: 10" in content
        assert "Test body content" in content
        
        mock_client.get_question_details.assert_called_once_with(123, include_answers=True)
    
    @pytest.mark.asyncio
    async def test_get_question_tool_missing_id(self, server):
        """Test get question tool with missing ID."""
        result = await server._handle_get_question({})
        
        assert "content" in result
        assert "Error: question_id is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_search_by_tags_tool_success(self, server):
        """Test successful tag search tool call."""
        mock_client = AsyncMock()
        mock_client.search_by_tags.return_value = {
            "items": [
                {
                    "question_id": 789,
                    "title": "How to use Python asyncio?",
                    "score": 20,
                    "view_count": 400,
                    "answer_count": 4,
                    "tags": ["python", "asyncio"],
                    "link": "https://stackoverflow.com/questions/789"
                }
            ],
            "total": 1
        }
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_search_by_tags({
            "tags": ["python", "asyncio"],
            "limit": 10,
            "page": 1,
            "sort": "activity"
        })
        
        assert "content" in result
        content = result["content"][0]["text"]
        assert "Found 1 questions for tags: python, asyncio" in content
        assert "How to use Python asyncio?" in content
        assert "ID: 789" in content
        assert "Score: 20" in content
        
        mock_client.search_by_tags.assert_called_once_with(
            tags=["python", "asyncio"],
            page=1,
            page_size=10,
            sort="activity"
        )

    @pytest.mark.asyncio
    async def test_search_by_tags_tool_empty_tags(self, server):
        """Test tag search tool with empty tags."""
        result = await server._handle_search_by_tags({"tags": []})
        
        assert "content" in result
        assert "Error: Tags cannot be empty" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_search_by_tags_tool_no_results(self, server):
        """Test tag search tool with no results."""
        mock_client = AsyncMock()
        mock_client.search_by_tags.return_value = {
            "items": [],
            "total": 0
        }
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_search_by_tags({"tags": ["nonexistent", "tag"]})
        
        assert "content" in result
        assert "No questions found for tags: nonexistent, tag" in result["content"][0]["text"]


class TestIntegration:
    """Integration tests for search functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        config = ServerConfig(max_requests_per_minute=2, retry_delay=0.1)
        client = StackOverflowClient(config)
        
        # Mock the actual HTTP request
        with patch.object(client.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"items": [], "total": 0}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Make requests that should trigger rate limiting
            import time
            start_time = time.time()
            
            await client.search_questions("test1")
            await client.search_questions("test2")
            # Third request should be rate limited
            await client.search_questions("test3")
            
            end_time = time.time()
            
            # Should have taken some time due to rate limiting
            assert end_time - start_time >= 0.1  # At least the retry delay 