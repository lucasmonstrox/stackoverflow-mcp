#!/usr/bin/env python3
"""
Test real StackOverflow API question details functionality.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.stackoverflow_client import StackOverflowClient
from stackoverflow_mcp.server import StackOverflowMCPServer


async def test_real_question_details():
    """Test real question details functionality."""
    print("Testing real StackOverflow API question details...")
    
    config = ServerConfig()
    
    async with StackOverflowClient(config) as client:
        try:
            # Test getting details for a well-known question
            print("\n1. Testing question details for a popular Python question...")
            question_id = 231767  # "What does the 'yield' keyword do?"
            
            question = await client.get_question_details(question_id, include_answers=True)
            
            print(f"Question ID: {question.get('question_id')}")
            print(f"Title: {question.get('title', 'No title')}")
            print(f"Score: {question.get('score', 0)}")
            print(f"View count: {question.get('view_count', 0):,}")
            print(f"Answer count: {question.get('answer_count', 0)}")
            print(f"Tags: {', '.join(question.get('tags', []))}")
            
            # Test HTML to Markdown conversion
            body = question.get('body', '')
            if body:
                markdown_body = client._convert_html_to_markdown(body)
                print(f"\nQuestion body (first 200 chars):")
                print(f"HTML: {body[:200]}...")
                print(f"Markdown: {markdown_body[:200]}...")
            
            # Test answers
            answers = question.get('answers', [])
            if answers:
                print(f"\nAnswers ({len(answers)} total):")
                for i, answer in enumerate(answers[:3], 1):
                    score = answer.get('score', 0)
                    is_accepted = answer.get('is_accepted', False)
                    accepted_marker = " ✅" if is_accepted else ""
                    print(f"{i}. Score: {score}{accepted_marker}")
                    
                    # Test answer body conversion
                    answer_body = answer.get('body', '')
                    if answer_body:
                        markdown_answer = client._convert_html_to_markdown(answer_body)
                        print(f"   Answer body (first 100 chars): {markdown_answer[:100]}...")
            
            print("\n✅ Question details test passed!")
            
        except Exception as e:
            print(f"❌ Error testing question details: {e}")
            return False
    
    return True


async def test_mcp_server_question_tools():
    """Test MCP server question tools."""
    print("\n2. Testing MCP server question tools...")
    
    config = ServerConfig()
    server = StackOverflowMCPServer(config)
    
    try:
        # Test basic get_question tool
        print("\nTesting get_question tool...")
        result = await server._handle_get_question({
            "question_id": 231767,
            "include_answers": True,
            "convert_to_markdown": True
        })
        
        content = result["content"][0]["text"]
        print(f"Basic question result (first 300 chars):")
        print(content[:300] + "...")
        
        # Test comprehensive get_question_with_answers tool
        print("\nTesting get_question_with_answers tool...")
        result = await server._handle_get_question_with_answers({
            "question_id": 231767,
            "max_answers": 2,
            "convert_to_markdown": True
        })
        
        content = result["content"][0]["text"]
        print(f"Comprehensive question result (first 500 chars):")
        print(content[:500] + "...")
        
        # Verify format
        assert "# " in content  # Title header
        assert "**Question ID:**" in content
        assert "## Question" in content
        assert "## Answers" in content or "*No answers available*" in content
        
        print("\n✅ MCP server question tools test passed!")
        
    except Exception as e:
        print(f"❌ Error testing MCP server tools: {e}")
        return False
    finally:
        # Clean up
        if server.stackoverflow_client:
            await server.stackoverflow_client.__aexit__(None, None, None)
    
    return True


async def main():
    """Run all tests."""
    print("🚀 Starting real StackOverflow question details API tests...")
    
    success = True
    
    # Test client functionality
    success &= await test_real_question_details()
    
    # Test MCP server tools
    success &= await test_mcp_server_question_tools()
    
    if success:
        print("\n🎉 All question details tests passed!")
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 