"""
Tests for StackOverflow question details functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from stackoverflow_mcp.config import ServerConfig
from stackoverflow_mcp.stackoverflow_client import StackOverflowClient
from stackoverflow_mcp.server import StackOverflowMCPServer


class TestQuestionDetailsClient:
    """Test StackOverflow question details client functionality."""
    
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
    async def test_get_question_details_with_answers(self, client):
        """Test getting question details with answers."""
        mock_question_response = {
            "items": [
                {
                    "question_id": 123,
                    "title": "How to test Python code?",
                    "body": "<p>I want to test my Python code. How do I do this?</p>",
                    "score": 15,
                    "view_count": 500,
                    "answer_count": 3,
                    "tags": ["python", "testing"],
                    "link": "https://stackoverflow.com/questions/123",
                    "creation_date": 1640995200,
                    "owner": {"display_name": "TestUser"}
                }
            ]
        }
        
        mock_answers_response = {
            "items": [
                {
                    "answer_id": 456,
                    "body": "<p>Use pytest for testing Python code.</p>",
                    "score": 25,
                    "is_accepted": True,
                    "creation_date": 1640995800,
                    "owner": {"display_name": "AnswerUser"}
                },
                {
                    "answer_id": 789,
                    "body": "<p>You can also use unittest module.</p>",
                    "score": 10,
                    "is_accepted": False,
                    "creation_date": 1640996000,
                    "owner": {"display_name": "OtherUser"}
                }
            ]
        }
        
        with patch.object(client, '_make_raw_request') as mock_request:
            mock_request.side_effect = [mock_question_response, mock_answers_response]
            
            result = await client.get_question_details(123, include_answers=True)
            
            # Check that question details were retrieved
            assert result["question_id"] == 123
            assert result["title"] == "How to test Python code?"
            assert "answers" in result
            assert len(result["answers"]) == 2
            assert result["answers"][0]["answer_id"] == 456
            assert result["answers"][1]["answer_id"] == 789
            
            # Check that both requests were made
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_question_details_without_answers(self, client):
        """Test getting question details without answers."""
        mock_response = {
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
        
        with patch.object(client, '_make_raw_request', return_value=mock_response) as mock_request:
            result = await client.get_question_details(123, include_answers=False)
            
            assert result["question_id"] == 123
            assert "answers" not in result
            
            # Only one API call should be made
            assert mock_request.call_count == 1
    
    def test_convert_html_to_markdown(self, client):
        """Test HTML to Markdown conversion."""
        html_content = "<p>This is a <strong>test</strong> with <code>code</code>.</p>"
        
        # Mock markdownify
        with patch('markdownify.markdownify') as mock_markdownify:
            mock_markdownify.return_value = "This is a **test** with `code`.\n\n"
            
            result = client._convert_html_to_markdown(html_content)
            
            assert "**test**" in result
            assert "`code`" in result
            mock_markdownify.assert_called_once()
    
    def test_convert_html_to_markdown_fallback(self, client):
        """Test HTML to Markdown conversion fallback when markdownify is not available."""
        html_content = "<p>Test content</p>"
        
        with patch('markdownify.markdownify', side_effect=ImportError()):
            result = client._convert_html_to_markdown(html_content)
            
            # Should return original HTML when markdownify is not available
            assert result == html_content


class TestQuestionDetailsMCPServer:
    """Test MCP server question details functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ServerConfig()
    
    @pytest.fixture
    def server(self, config):
        """Create test server."""
        return StackOverflowMCPServer(config)
    
    @pytest.mark.asyncio
    async def test_get_question_tool_enhanced(self, server):
        """Test enhanced get_question tool."""
        mock_client = AsyncMock()
        mock_client.get_question_details.return_value = {
            "question_id": 123,
            "title": "Test Question",
            "body": "Test body content",
            "score": 10,
            "view_count": 100,
            "answer_count": 2,
            "tags": ["python"],
            "link": "https://stackoverflow.com/questions/123",
            "answers": [
                {"score": 15, "is_accepted": True},
                {"score": 5, "is_accepted": False}
            ]
        }
        # Mock as regular method, not async
        mock_client._convert_html_to_markdown = MagicMock(return_value="Test body content")
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_get_question({
            "question_id": 123,
            "include_answers": True,
            "convert_to_markdown": True
        })
        
        assert "content" in result
        content = result["content"][0]["text"]
        assert "Test Question" in content
        assert "ID: 123" in content
        assert "Answers (2 total)" in content
        assert "✅" in content  # Accepted answer marker
        
        mock_client.get_question_details.assert_called_once_with(123, include_answers=True)
    
    @pytest.mark.asyncio
    async def test_get_question_with_answers_tool(self, server):
        """Test get_question_with_answers tool."""
        mock_client = AsyncMock()
        mock_client.get_question_details.return_value = {
            "question_id": 456,
            "title": "Comprehensive Question",
            "body": "<p>Question body with HTML</p>",
            "score": 20,
            "view_count": 1000,
            "answer_count": 1,
            "tags": ["python", "testing"],
            "link": "https://stackoverflow.com/questions/456",
            "creation_date": 1640995200,
            "owner": {"display_name": "QuestionAuthor"},
            "answers": [
                {
                    "answer_id": 789,
                    "body": "<p>Detailed answer with HTML</p>",
                    "score": 30,
                    "is_accepted": True,
                    "creation_date": 1640996000,
                    "owner": {"display_name": "AnswerAuthor"}
                }
            ]
        }
        # Mock as regular method, not async
        mock_client._convert_html_to_markdown = MagicMock(side_effect=[
            "Question body with HTML",  # For question
            "Detailed answer with HTML"  # For answer
        ])
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_get_question_with_answers({
            "question_id": 456,
            "max_answers": 5,
            "convert_to_markdown": True
        })
        
        assert "content" in result
        content = result["content"][0]["text"]
        assert "# Comprehensive Question" in content
        assert "**Question ID:** 456" in content
        assert "## Question" in content
        assert "## Answers" in content
        assert "### Answer 1 ✅ **ACCEPTED**" in content
        assert "**Score:** 30 |" in content
        assert "**Author:** AnswerAuthor |" in content
        
        mock_client.get_question_details.assert_called_once_with(456, include_answers=True)
        # Should call markdown conversion twice (question + answer)
        assert mock_client._convert_html_to_markdown.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_question_with_answers_no_answers(self, server):
        """Test get_question_with_answers when no answers exist."""
        mock_client = AsyncMock()
        mock_client.get_question_details.return_value = {
            "question_id": 999,
            "title": "Unanswered Question",
            "body": "Question without answers",
            "score": 5,
            "view_count": 50,
            "answer_count": 0,
            "tags": ["new-tag"],
            "link": "https://stackoverflow.com/questions/999",
            "creation_date": 1640995200,
            "owner": {"display_name": "NewUser"},
            "answers": []
        }
        # Mock as regular method, not async
        mock_client._convert_html_to_markdown = MagicMock(return_value="Question without answers")
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_get_question_with_answers({
            "question_id": 999,
            "convert_to_markdown": True
        })
        
        assert "content" in result
        content = result["content"][0]["text"]
        assert "# Unanswered Question" in content
        assert "*No answers available for this question.*" in content
    
    @pytest.mark.asyncio
    async def test_get_question_with_answers_max_limit(self, server):
        """Test get_question_with_answers with answer limit."""
        mock_answers = []
        for i in range(10):
            mock_answers.append({
                "answer_id": 100 + i,
                "body": f"Answer {i+1} content",
                "score": 10 - i,
                "is_accepted": i == 0,
                "creation_date": 1640995200 + i * 3600,
                "owner": {"display_name": f"User{i+1}"}
            })
        
        mock_client = AsyncMock()
        mock_client.get_question_details.return_value = {
            "question_id": 888,
            "title": "Popular Question",
            "body": "Question with many answers",
            "score": 50,
            "view_count": 5000,
            "answer_count": 10,
            "tags": ["popular"],
            "link": "https://stackoverflow.com/questions/888",
            "creation_date": 1640995200,
            "owner": {"display_name": "PopularUser"},
            "answers": mock_answers
        }
        # Mock as regular method, not async
        mock_client._convert_html_to_markdown = MagicMock(side_effect=[
            "Question with many answers"
        ] + [f"Answer {i+1} content" for i in range(3)])  # Only first 3 answers will be processed
        
        server.stackoverflow_client = mock_client
        
        result = await server._handle_get_question_with_answers({
            "question_id": 888,
            "max_answers": 3,
            "convert_to_markdown": True
        })
        
        assert "content" in result
        content = result["content"][0]["text"]
        assert "### Answer 1 ✅ **ACCEPTED**" in content
        assert "### Answer 2" in content
        assert "### Answer 3" in content
        assert "### Answer 4" not in content  # Should not include 4th answer
        assert "7 more answer(s) available" in content  # Should note remaining answers


class TestIntegrationQuestionDetails:
    """Integration tests for question details functionality."""
    
    @pytest.mark.asyncio
    async def test_question_details_workflow(self):
        """Test complete question details workflow."""
        config = ServerConfig(max_requests_per_minute=10, retry_delay=0.1)
        server = StackOverflowMCPServer(config)
        
        # Mock the client methods
        with patch.object(server, '_ensure_client'):
            mock_client = AsyncMock()
            server.stackoverflow_client = mock_client
            
            # Test basic question details
            mock_client.get_question_details.return_value = {
                "question_id": 777,
                "title": "Integration Test Question",
                "body": "Test body",
                "score": 25,
                "view_count": 2000,
                "answer_count": 1,
                "tags": ["integration", "test"],
                "link": "https://stackoverflow.com/questions/777",
                "answers": [{"score": 20, "is_accepted": True}]
            }
            # Mock as regular method, not async
            mock_client._convert_html_to_markdown = MagicMock(return_value="Test body")
            
            # Test the workflow
            result = await server._handle_get_question({
                "question_id": 777,
                "include_answers": True
            })
            
            assert "content" in result
            content = result["content"][0]["text"]
            assert "Integration Test Question" in content
            assert "Score: 25" in content
            assert "Answers (1 total)" in content 