"""
Configuration management for StackOverflow MCP server.
"""

import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv


class ServerConfig(BaseModel):
    """Configuration settings for the MCP server."""
    
    # Server settings
    host: str = "localhost"
    port: int = 3000
    
    # StackOverflow API settings
    stackoverflow_api_key: Optional[str] = None
    stackoverflow_base_url: str = "https://api.stackexchange.com/2.3"
    
    # Rate limiting settings
    max_requests_per_minute: int = 30
    retry_delay: float = 1.0
    
    # Content settings
    max_content_length: int = 50000  # Maximum content length before truncation
    cache_ttl: int = 300  # 5 minutes
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def load_from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables and .env file."""
        load_dotenv()
        
        return cls(
            host=os.getenv("MCP_HOST", "localhost"),
            port=int(os.getenv("MCP_PORT", "3000")),
            stackoverflow_api_key=os.getenv("STACKOVERFLOW_API_KEY"),
            stackoverflow_base_url=os.getenv(
                "STACKOVERFLOW_BASE_URL", 
                "https://api.stackexchange.com/2.3"
            ),
            max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30")),
            retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "50000")),
            cache_ttl=int(os.getenv("CACHE_TTL", "300")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ) 