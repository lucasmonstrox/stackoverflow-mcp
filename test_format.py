#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unittest.mock import AsyncMock, MagicMock
from stackoverflow_mcp.server import StackOverflowMCPServer
from stackoverflow_mcp.config import ServerConfig

async def test_output():
    server = StackOverflowMCPServer(ServerConfig())
    mock_client = AsyncMock()
    mock_client.get_question_details.return_value = {
        'question_id': 456,
        'title': 'Test Question',
        'body': 'Question body',
        'score': 20,
        'view_count': 1000,
        'answer_count': 1,
        'tags': ['python'],
        'link': 'https://stackoverflow.com/questions/456',
        'creation_date': 1640995200,
        'owner': {'display_name': 'Author'},
        'answers': [{
            'answer_id': 789,
            'body': 'Answer body',
            'score': 30,
            'is_accepted': True,
            'creation_date': 1640996000,
            'owner': {'display_name': 'AnswerAuthor'}
        }]
    }
    mock_client._convert_html_to_markdown = MagicMock(side_effect=['Question body', 'Answer body'])
    server.stackoverflow_client = mock_client
    
    result = await server._handle_get_question_with_answers({'question_id': 456, 'convert_to_markdown': True})
    print('OUTPUT:')
    content = result['content'][0]['text']
    print(content)
    print('\nSplit lines:')
    for i, line in enumerate(content.split('\n')):
        print(f"{i:2}: {repr(line)}")

if __name__ == "__main__":
    asyncio.run(test_output()) 