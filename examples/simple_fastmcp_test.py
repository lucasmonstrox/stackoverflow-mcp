#!/usr/bin/env python3
"""
Simple test to verify FastMcp StackOverflow server functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.fastmcp_server import create_app


async def test_fastmcp_app():
    """Test FastMcp app creation and tool registration."""
    print("Testing FastMcp StackOverflow Server...")
    
    # Create configuration
    config = ServerConfig(
        host="localhost",
        port=3000,
        log_level="INFO"
    )
    
    # Create app
    app = create_app(config)
    print(f"✅ Created FastMcp app: {app.name}")
    
    # Test tools
    try:
        tools = await app.get_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool_name, tool in tools.items():
            print(f"   - {tool_name}: {tool.description}")
    except Exception as e:
        print(f"❌ Error getting tools: {e}")
    
    # Test resources
    try:
        resources = await app.get_resources()
        print(f"✅ Found {len(resources)} resources:")
        for resource_uri, resource in resources.items():
            print(f"   - {resource_uri}: {resource.description}")
    except Exception as e:
        print(f"❌ Error getting resources: {e}")
    
    print("\n🎉 FastMcp server validation complete!")
    
    return app


async def test_tool_schemas():
    """Test that tool schemas are properly generated."""
    print("\nTesting tool schema generation...")
    
    config = ServerConfig()
    app = create_app(config)
    
    tools = await app.get_tools()
    
    # Check search_questions tool
    if "search_questions" in tools:
        tool = tools["search_questions"]
        print(f"✅ search_questions tool found")
        print(f"   Description: {tool.description}")
        
        # Check if schema is properly generated
        if hasattr(tool, 'input_schema') and tool.input_schema:
            schema = tool.input_schema
            print(f"   Schema properties: {list(schema.get('properties', {}).keys())}")
            
            # Verify required parameters
            required = schema.get('required', [])
            if 'query' in required:
                print(f"   ✅ Required parameter 'query' found")
            else:
                print(f"   ❌ Required parameter 'query' missing")
        else:
            print(f"   ❌ No input schema found")
    else:
        print(f"❌ search_questions tool not found")


if __name__ == "__main__":
    async def main():
        await test_fastmcp_app()
        await test_tool_schemas()
    
    asyncio.run(main()) 