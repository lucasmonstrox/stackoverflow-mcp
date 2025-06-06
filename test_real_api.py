#!/usr/bin/env python3
"""
Test script for real StackOverflow API functionality.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.stackoverflow_client import StackOverflowClient
from stackoverflow_mcp.server import StackOverflowMCPServer


async def test_real_search():
    """Test real search functionality."""
    print("Testing real StackOverflow API search...")
    
    config = ServerConfig()
    
    async with StackOverflowClient(config) as client:
        try:
            # Test keyword search
            print("\n1. Testing search for 'python async'...")
            result = await client.search_questions("python async", page_size=3)
            
            print(f"Found {result.get('total', 0)} total results")
            print(f"Returned {len(result.get('items', []))} items")
            
            for i, question in enumerate(result.get('items', [])[:2], 1):
                print(f"\n{i}. {question.get('title', 'No title')}")
                print(f"   ID: {question.get('question_id')}")
                print(f"   Score: {question.get('score')}")
                print(f"   Tags: {', '.join(question.get('tags', []))}")
            
            # Test tag search
            print(f"\n2. Testing tag search for ['python', 'asyncio']...")
            tag_result = await client.search_by_tags(["python", "asyncio"], page_size=3)
            
            print(f"Found {tag_result.get('total', 0)} total results")
            print(f"Returned {len(tag_result.get('items', []))} items")
            
            for i, question in enumerate(tag_result.get('items', [])[:2], 1):
                print(f"\n{i}. {question.get('title', 'No title')}")
                print(f"   ID: {question.get('question_id')}")
                print(f"   Score: {question.get('score')}")
                print(f"   Tags: {', '.join(question.get('tags', []))}")
            
            # Test get question details if we have results
            if result.get('items'):
                question_id = result['items'][0]['question_id']
                print(f"\n3. Testing get question details for ID {question_id}...")
                
                details = await client.get_question_details(question_id)
                print(f"Title: {details.get('title', 'No title')}")
                print(f"Body length: {len(details.get('body', ''))}")
                print(f"Answer count: {details.get('answer_count', 0)}")
            
            print("\n✅ Real API test completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error during real API test: {e}")
            return False
    
    return True


async def test_mcp_server_tools():
    """Test MCP server tools."""
    print("\nTesting MCP server tools...")
    
    config = ServerConfig()
    server = StackOverflowMCPServer(config)
    
    try:
        # Test search tool
        print("\n1. Testing search_questions tool...")
        result = await server._handle_search_questions({
            "query": "python testing",
            "limit": 3,
            "sort": "votes"
        })
        
        content = result.get('content', [{}])[0].get('text', '')
        print(f"Search result preview: {content[:200]}...")
        
        # Test tag search tool
        print("\n2. Testing search_by_tags tool...")
        result = await server._handle_search_by_tags({
            "tags": ["python", "unittest"],
            "limit": 3,
            "sort": "votes"
        })
        
        content = result.get('content', [{}])[0].get('text', '')
        print(f"Tag search result preview: {content[:200]}...")
        
        # Test get question tool (using a well-known question ID)
        print("\n3. Testing get_question tool...")
        result = await server._handle_get_question({
            "question_id": 11227809  # "Why is processing a sorted array faster than processing an unsorted array?"
        })
        
        content = result.get('content', [{}])[0].get('text', '')
        print(f"Question result preview: {content[:200]}...")
        
        print("\n✅ MCP server tools test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during MCP server test: {e}")
        return False
    finally:
        if server.stackoverflow_client:
            await server.stackoverflow_client.__aexit__(None, None, None)
    
    return True


async def main():
    """Main test function."""
    print("🚀 Starting StackOverflow MCP Server Tests")
    print("=" * 50)
    
    success = True
    
    # Test real API
    success &= await test_real_search()
    
    # Test MCP server tools
    success &= await test_mcp_server_tools()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed!")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 