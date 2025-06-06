"""
Tests for request queue and auto-switching functionality.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.stackoverflow_client import (
    StackOverflowClient, RequestQueue, RequestCache, QueuedRequest,
    RequestPriority, AccessMode
)
from stackoverflow_mcp.server import StackOverflowMCPServer


class TestRequestCache:
    """Test RequestCache functionality."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = RequestCache(max_size=100, ttl_seconds=60)
        assert cache.max_size == 100
        assert cache.ttl_seconds == 60
        assert len(cache._cache) == 0
    
    def test_cache_set_get(self):
        """Test basic cache operations."""
        cache = RequestCache(max_size=100, ttl_seconds=60)
        
        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")
        
        assert result == {"data": "value1"}
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        cache = RequestCache(max_size=100, ttl_seconds=0.1)  # 100ms TTL
        
        cache.set("key1", {"data": "value1"})
        
        # Should be available immediately
        assert cache.get("key1") is not None
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        assert cache.get("key1") is None
    
    def test_cache_eviction(self):
        """Test cache LRU eviction."""
        cache = RequestCache(max_size=2, ttl_seconds=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Cache is full, adding third item should evict oldest
        cache.set("key3", "value3")
        
        # key1 should be evicted (oldest)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = RequestCache(max_size=100, ttl_seconds=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["max_size"] == 100
        assert stats["ttl_seconds"] == 60


class TestQueuedRequest:
    """Test QueuedRequest functionality."""
    
    def test_queued_request_creation(self):
        """Test creation of queued request."""
        request = QueuedRequest(
            id="test_req_1",
            endpoint="questions",
            params={"site": "stackoverflow"},
            priority=RequestPriority.NORMAL,
            created_at=time.time()
        )
        
        assert request.id == "test_req_1"
        assert request.endpoint == "questions"
        assert request.priority == RequestPriority.NORMAL
        assert request.retry_count == 0
        assert request.max_retries == 3
        assert request.access_mode == AccessMode.AUTO
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        request1 = QueuedRequest(
            id="req1",
            endpoint="questions",
            params={"site": "stackoverflow", "page": 1},
            priority=RequestPriority.NORMAL,
            created_at=time.time()
        )
        
        request2 = QueuedRequest(
            id="req2",
            endpoint="questions",
            params={"page": 1, "site": "stackoverflow"},  # Same params, different order
            priority=RequestPriority.HIGH,  # Different priority
            created_at=time.time()
        )
        
        # Should generate same cache key despite different order and priority
        assert request1.get_cache_key() == request2.get_cache_key()
    
    def test_cache_key_different_params(self):
        """Test cache key generation with different parameters."""
        request1 = QueuedRequest(
            id="req1",
            endpoint="questions",
            params={"site": "stackoverflow", "page": 1},
            priority=RequestPriority.NORMAL,
            created_at=time.time()
        )
        
        request2 = QueuedRequest(
            id="req2",
            endpoint="questions",
            params={"site": "stackoverflow", "page": 2},  # Different page
            priority=RequestPriority.NORMAL,
            created_at=time.time()
        )
        
        # Should generate different cache keys
        assert request1.get_cache_key() != request2.get_cache_key()


class TestRequestQueue:
    """Test RequestQueue functionality."""
    
    @pytest.fixture
    def queue(self):
        """Create test queue."""
        return RequestQueue(max_concurrent=2)
    
    @pytest.mark.asyncio
    async def test_queue_initialization(self, queue):
        """Test queue initialization."""
        assert queue.max_concurrent == 2
        assert len(queue._queue) == 0
        assert len(queue._processing) == 0
        assert len(queue._completed) == 0
    
    def test_queue_status(self, queue):
        """Test queue status reporting."""
        status = queue.get_status()
        
        assert "queued" in status
        assert "processing" in status
        assert "completed" in status
        assert "max_concurrent" in status
        assert "worker_running" in status
        
        assert status["queued"] == 0
        assert status["processing"] == 0
        assert status["completed"] == 0
        assert status["max_concurrent"] == 2


class TestStackOverflowClientQueue:
    """Test StackOverflowClient with queue system."""
    
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
    
    def test_client_initialization_with_queue(self, client):
        """Test client initialization with queue system."""
        assert client.request_queue is not None
        assert client.cache is not None
        assert client.auto_switch_enabled is True
        assert client.current_access_mode == AccessMode.AUTO
    
    def test_access_mode_decision_no_api_key(self, client):
        """Test access mode decision without API key."""
        client.api_key = None
        
        result = client._should_use_authenticated_access(AccessMode.AUTO)
        assert result is False
        
        result = client._should_use_authenticated_access(AccessMode.AUTHENTICATED)
        assert result is True  # Force authenticated even without key
        
        result = client._should_use_authenticated_access(AccessMode.UNAUTHENTICATED)
        assert result is False
    
    def test_access_mode_decision_with_api_key(self, client):
        """Test access mode decision with API key."""
        client.api_key = "test-key"
        client.auth_state.set_authentication_status(True)
        
        result = client._should_use_authenticated_access(AccessMode.AUTO)
        assert result is True
        
        result = client._should_use_authenticated_access(AccessMode.AUTHENTICATED)
        assert result is True
        
        result = client._should_use_authenticated_access(AccessMode.UNAUTHENTICATED)
        assert result is False
    
    def test_access_mode_decision_low_quota(self, client):
        """Test access mode decision with low quota."""
        client.api_key = "test-key"
        client.auth_state.set_authentication_status(True)
        client.auth_state.update_quota_info(10000, 30)  # Low remaining quota
        
        result = client._should_use_authenticated_access(AccessMode.AUTO)
        assert result is False  # Should switch to unauthenticated
    
    def test_access_mode_decision_rate_limited(self, client):
        """Test access mode decision when rate limited."""
        client.api_key = "test-key"
        client.auth_state.set_authentication_status(True)
        client.rate_limit_state.set_rate_limited(60.0)  # Rate limited
        
        result = client._should_use_authenticated_access(AccessMode.AUTO)
        assert result is False  # Should switch to unauthenticated
    
    def test_queue_status_reporting(self, client):
        """Test queue status reporting."""
        status = client.get_queue_status()
        
        assert "queue" in status
        assert "cache" in status
        assert "auto_switch_enabled" in status
        assert "current_access_mode" in status
        
        assert isinstance(status["queue"], dict)
        assert isinstance(status["cache"], dict)
        assert status["auto_switch_enabled"] is True
        assert status["current_access_mode"] == "auto"


class TestMCPQueueStatus:
    """Test MCP queue status tool."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ServerConfig(
            stackoverflow_api_key="test-key",
            max_requests_per_minute=30,
            retry_delay=1.0
        )
    
    @pytest.fixture
    def server(self, config):
        """Create test server."""
        return StackOverflowMCPServer(config)
    
    @pytest.mark.asyncio
    async def test_queue_status_tool(self, server):
        """Test get_queue_status MCP tool."""
        # Initialize client manually
        server.stackoverflow_client = StackOverflowClient(server.config)
        
        result = await server._handle_get_queue_status({})
        
        assert "content" in result
        assert len(result["content"]) == 1
        text = result["content"][0]["text"]
        assert "StackOverflow MCP Request Queue Status" in text
        assert "## Queue Information" in text
        assert "**Queued Requests:**" in text
        assert "**Processing Requests:**" in text
        assert "## Cache Statistics" in text
        assert "**Total Entries:**" in text
        assert "## Auto-Switching Configuration" in text
        assert "**Auto-Switch Enabled:** Yes" in text
        assert "**Current Access Mode:** auto" in text 