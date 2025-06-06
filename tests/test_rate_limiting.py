"""
Tests for enhanced rate limiting functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import time
import asyncio

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.stackoverflow_client import StackOverflowClient, RateLimitState
from stackoverflow_mcp.server import StackOverflowMCPServer


class TestRateLimitState:
    """Test RateLimitState class functionality."""
    
    def test_rate_limit_state_initialization(self):
        """Test initial state."""
        state = RateLimitState()
        assert not state.is_rate_limited
        assert state.backoff_until == 0.0
        assert state.current_backoff == 1.0
        assert state.max_backoff == 300.0
        assert state.remaining_requests is None
        assert state.reset_time is None
    
    def test_update_from_headers(self):
        """Test header parsing."""
        state = RateLimitState()
        
        headers = {
            'x-ratelimit-remaining': '25',
            'x-ratelimit-reset': '1609459200'
        }
        
        state.update_from_headers(headers)
        assert state.remaining_requests == 25
        assert state.reset_time == 1609459200
    
    def test_update_from_headers_invalid(self):
        """Test header parsing with invalid values."""
        state = RateLimitState()
        
        headers = {
            'x-ratelimit-remaining': 'invalid',
            'x-ratelimit-reset': 'also-invalid'
        }
        
        state.update_from_headers(headers)
        assert state.remaining_requests is None
        assert state.reset_time is None
    
    def test_set_rate_limited_with_backoff(self):
        """Test setting rate limited state with specific backoff."""
        state = RateLimitState()
        current_time = time.time()
        
        state.set_rate_limited(60.0)
        
        assert state.is_rate_limited
        assert abs(state.backoff_until - (current_time + 60.0)) < 1.0
        assert state.current_backoff == 60.0
    
    def test_set_rate_limited_exponential_backoff(self):
        """Test exponential backoff."""
        state = RateLimitState()
        
        # First rate limit
        state.set_rate_limited()
        # After first call, backoff is doubled from 1.0 to 2.0
        assert state.current_backoff == 2.0
        
        # Second rate limit (should double again)
        state.set_rate_limited()
        assert state.current_backoff == 4.0
        
        # Third rate limit (should double again)
        state.set_rate_limited()
        assert state.current_backoff == 8.0
    
    def test_check_recovery(self):
        """Test rate limit recovery."""
        state = RateLimitState()
        
        # Set rate limited with very short backoff
        state.set_rate_limited(0.1)
        assert state.is_rate_limited
        
        # Should not recover immediately
        assert not state.check_recovery()
        assert state.is_rate_limited
        
        # Wait for backoff to expire
        time.sleep(0.2)
        
        # Should recover now
        assert state.check_recovery()
        assert not state.is_rate_limited


class TestEnhancedRateLimiting:
    """Test enhanced rate limiting in StackOverflowClient."""
    
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
    async def test_429_status_code_handling(self, client):
        """Test handling of 429 status code."""
        with patch.object(client.session, 'get') as mock_get:
            # Mock 429 response
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {'retry-after': '30'}
            mock_get.return_value = mock_response
            
            # Should raise exception with friendly message
            with pytest.raises(Exception, match="rate limit exceeded"):
                await client.search_questions("test")
            
            # Should have set rate limited state
            assert client.rate_limit_state.is_rate_limited
            assert client.rate_limit_state.current_backoff == 30.0
    
    @pytest.mark.asyncio
    async def test_429_without_retry_after(self, client):
        """Test 429 handling without retry-after header."""
        with patch.object(client.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {}
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception, match="rate limit exceeded"):
                await client.search_questions("test")
            
            # Should use exponential backoff (1.0 -> 2.0 after first call)
            assert client.rate_limit_state.is_rate_limited
            assert client.rate_limit_state.current_backoff == 2.0
    
    @pytest.mark.asyncio
    async def test_server_error_backoff(self, client):
        """Test backoff for server errors."""
        with patch.object(client.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_response.text = "Service Unavailable"
            mock_get.side_effect = httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=MagicMock(),
                response=mock_response
            )
            
            with pytest.raises(Exception, match="HTTP error 503"):
                await client.search_questions("test")
            
            # Should have set rate limited with 30s backoff
            assert client.rate_limit_state.is_rate_limited
            assert client.rate_limit_state.current_backoff == 30.0
    
    @pytest.mark.asyncio
    async def test_header_monitoring(self, client):
        """Test rate limit header monitoring."""
        with patch.object(client.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {
                'x-ratelimit-remaining': '5',
                'x-ratelimit-reset': str(int(time.time()) + 3600)
            }
            mock_response.json.return_value = {"items": [], "total": 0}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.search_questions("test")
            
            # Should have updated state from headers
            assert client.rate_limit_state.remaining_requests == 5
            assert client.rate_limit_state.reset_time is not None
    
    @pytest.mark.asyncio
    async def test_dynamic_interval_adjustment(self, client):
        """Test dynamic request interval based on remaining quota."""
        # Mock low remaining requests
        client.rate_limit_state.remaining_requests = 3
        
        with patch.object(client.session, 'get') as mock_get, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = {"items": [], "total": 0}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.search_questions("test")
            
            # Should have applied extra delay for low quota
            # extra_delay = (10 - 3) * 0.5 = 3.5 seconds
            mock_sleep.assert_any_call(3.5)
    
    @pytest.mark.asyncio
    async def test_api_error_rate_limit_detection(self, client):
        """Test detection of rate limit from API error messages."""
        with patch.object(client.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = {
                "error_id": 502,
                "error_message": "Request throttled due to quota exceeded"
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception, match="StackOverflow API error"):
                await client.search_questions("test")
            
            # Should have detected rate limiting from error message
            assert client.rate_limit_state.is_rate_limited
    
    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self, client):
        """Test rate limit recovery mechanism."""
        # Set rate limited with very short backoff
        client.rate_limit_state.set_rate_limited(0.1)
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = {"items": [], "total": 0}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Wait for recovery
            await asyncio.sleep(0.2)
            
            # Should recover and allow requests
            await client.search_questions("test")
            assert not client.rate_limit_state.is_rate_limited
    
    def test_get_rate_limit_status(self, client):
        """Test rate limit status reporting."""
        # Set some test state
        client.rate_limit_state.remaining_requests = 15
        client.rate_limit_state.reset_time = int(time.time()) + 3600
        client._request_count = 5
        
        status = client.get_rate_limit_status()
        
        assert "is_rate_limited" in status
        assert "remaining_requests" in status
        assert "reset_time" in status
        assert "requests_this_window" in status
        assert status["remaining_requests"] == 15
        assert status["requests_this_window"] == 5


class TestMCPRateLimitStatus:
    """Test MCP rate limit status tool."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ServerConfig(max_requests_per_minute=30, retry_delay=1.0)
    
    @pytest.fixture
    def server(self, config):
        """Create test server."""
        return StackOverflowMCPServer(config)
    
    @pytest.mark.asyncio
    async def test_rate_limit_status_tool(self, server):
        """Test get_rate_limit_status MCP tool."""
        # Initialize client manually
        server.stackoverflow_client = StackOverflowClient(server.config)
        
        # Set some test state
        server.stackoverflow_client.rate_limit_state.remaining_requests = 20
        server.stackoverflow_client._request_count = 10
        
        result = await server._handle_get_rate_limit_status({})
        
        assert "content" in result
        assert len(result["content"]) == 1
        assert "StackOverflow API Rate Limit Status" in result["content"][0]["text"]
        assert "**Rate Limited:** No" in result["content"][0]["text"]
        assert "**Remaining Requests:** 20" in result["content"][0]["text"]
        assert "**Requests This Window:** 10" in result["content"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_rate_limit_status_when_limited(self, server):
        """Test rate limit status when actually rate limited."""
        # Initialize client manually
        server.stackoverflow_client = StackOverflowClient(server.config)
        
        # Set rate limited state
        server.stackoverflow_client.rate_limit_state.set_rate_limited(120.0)
        
        result = await server._handle_get_rate_limit_status({})
        
        text = result["content"][0]["text"]
        assert "**Rate Limited:** Yes" in text
        assert "**Current Backoff:** 120.0 seconds" in text
        assert "**Wait Time:** " in text 