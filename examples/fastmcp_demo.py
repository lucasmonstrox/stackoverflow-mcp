#!/usr/bin/env python3
"""
FastMcp StackOverflow MCP Server Demo

This demonstrates the simplified FastMcp implementation compared to the traditional MCP approach.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.fastmcp_server import create_app, StackOverflowServer


async def demo_fastmcp():
    """Demonstrate FastMcp functionality."""
    print("=" * 60)
    print("StackOverflow MCP Server - FastMcp Demo")
    print("=" * 60)
    
    # Create configuration
    config = ServerConfig(
        host="localhost",
        port=3000,
        log_level="INFO"
    )
    
    # Create FastMcp app
    app = create_app(config)
    
    print(f"FastMcp app created with tools:")
    
    # Show available tools (these are auto-registered by FastMcp decorators)
    tools = [
        "search_questions",
        "search_by_tags", 
        "get_question",
        "get_question_with_answers",
        "get_rate_limit_status",
        "get_authentication_status",
        "get_queue_status"
    ]
    
    for tool in tools:
        print(f"  - {tool}")
    
    print(f"\nResources:")
    print(f"  - stackoverflow://status")
    
    print(f"\nKey FastMcp Benefits:")
    print(f"  ✅ Simple decorator-based tool definition")
    print(f"  ✅ Automatic type validation and schema generation")
    print(f"  ✅ Clean separation of concerns")
    print(f"  ✅ Reduced boilerplate (from ~978 lines to ~300 lines)")
    print(f"  ✅ Built-in resource management")
    print(f"  ✅ Elegant error handling")
    
    print(f"\nTo run the server:")
    print(f"  python -m stackoverflow_mcp.fastmcp_main")
    print(f"  # or")
    print(f"  stackoverflow-mcp-fastmcp")
    
    print("=" * 60)


async def comparison_demo():
    """Compare traditional MCP vs FastMcp approaches."""
    print("\n" + "=" * 60)
    print("COMPARISON: Traditional MCP vs FastMcp")
    print("=" * 60)
    
    print("TRADITIONAL MCP (server.py - 978 lines):")
    print("""
@self.server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    if self.stackoverflow_client is None:
        await self._ensure_client()
    
    if name == "search_questions":
        return await self._handle_search_questions(arguments)
    elif name == "search_by_tags":
        return await self._handle_search_by_tags(arguments)
    # ... many more elif statements
    else:
        raise ValueError(f"Unknown tool: {name}")

# Plus extensive manual schema definitions, error handling, etc.
    """)
    
    print("FASTMCP (fastmcp_server.py - ~300 lines):")
    print("""
@mcp.tool()
async def search_questions(
    query: str,
    limit: int = 10,
    page: int = 1,
    sort: str = "relevance"
) -> Dict[str, Any]:
    '''Search StackOverflow questions by keywords.'''
    await server.initialize()
    
    try:
        result = await server.client.search_questions(
            query=query, page=page, page_size=min(max(1, limit), 50),
            sort=sort, priority=RequestPriority.NORMAL
        )
        return result
    except Exception as e:
        return {"error": str(e), "success": False}
    """)
    
    print("KEY IMPROVEMENTS:")
    print("  🔥 67% less code (978 → 300 lines)")
    print("  🔥 Automatic schema generation from type hints")
    print("  🔥 Decorator-based tool registration")
    print("  🔥 Built-in error handling patterns")
    print("  🔥 Cleaner resource management")
    print("  🔥 No manual tool routing")
    
    print("=" * 60)


if __name__ == "__main__":
    print("FastMcp StackOverflow MCP Server Demo")
    
    async def main():
        await demo_fastmcp()
        await comparison_demo()
    
    asyncio.run(main()) 