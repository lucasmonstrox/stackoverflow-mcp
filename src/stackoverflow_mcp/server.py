"""
Core MCP server implementation for StackOverflow queries.
"""

import asyncio
import signal
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, Resource
from .config import ServerConfig
from .logging import get_logger
from .stackoverflow_client import StackOverflowClient


logger = get_logger("server")


class StackOverflowMCPServer:
    """Main MCP server class for StackOverflow queries."""
    
    def __init__(self, config: ServerConfig):
        """Initialize the MCP server with configuration."""
        self.config = config
        self.server = Server("stackoverflow-mcp")
        self.stackoverflow_client = None
        self._setup_handlers()
        self._shutdown_event = asyncio.Event()
        
    def _setup_handlers(self) -> None:
        """Setup MCP server handlers and capabilities."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools for StackOverflow queries."""
            return [
                Tool(
                    name="search_questions",
                    description="Search StackOverflow questions by keywords",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query keywords"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number for pagination",
                                "default": 1,
                                "minimum": 1
                            },
                            "sort": {
                                "type": "string",
                                "description": "Sort order",
                                "enum": ["relevance", "activity", "votes", "creation"],
                                "default": "relevance"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="search_by_tags",
                    description="Search StackOverflow questions by programming tags",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of tags to search for (e.g., ['python', 'async'])"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number for pagination",
                                "default": 1,
                                "minimum": 1
                            },
                            "sort": {
                                "type": "string",
                                "description": "Sort order",
                                "enum": ["activity", "votes", "creation", "relevance"],
                                "default": "activity"
                            }
                        },
                        "required": ["tags"]
                    }
                ),
                Tool(
                    name="get_question",
                    description="Get detailed information about a specific question",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question_id": {
                                "type": "integer",
                                "description": "StackOverflow question ID"
                            },
                            "include_answers": {
                                "type": "boolean",
                                "description": "Whether to include answers (default: true)",
                                "default": True
                            },
                            "convert_to_markdown": {
                                "type": "boolean", 
                                "description": "Convert HTML content to markdown (default: true)",
                                "default": True
                            }
                        },
                        "required": ["question_id"]
                    }
                ),
                Tool(
                    name="get_question_with_answers",
                    description="Get comprehensive question details including all answers",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question_id": {
                                "type": "integer",
                                "description": "StackOverflow question ID"
                            },
                            "max_answers": {
                                "type": "integer",
                                "description": "Maximum number of answers to include",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 20
                            },
                            "convert_to_markdown": {
                                "type": "boolean",
                                "description": "Convert HTML content to markdown (default: true)",
                                "default": True
                            }
                        },
                        "required": ["question_id"]
                    }
                ),
                Tool(
                    name="get_rate_limit_status",
                    description="Get current rate limiting status and quotas for monitoring",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                ),
                Tool(
                    name="get_authentication_status",
                    description="Get current API authentication status and quota information",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                ),
                Tool(
                    name="get_queue_status",
                    description="Get current request queue status, cache statistics, and auto-switching information",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri="stackoverflow://status",
                    name="Server Status",
                    description="Current server status and configuration",
                    mimeType="application/json"
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
            """Handle tool calls."""
            logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            # Initialize client if not already done
            if self.stackoverflow_client is None:
                logger.info("Initializing StackOverflow client")
                self.stackoverflow_client = StackOverflowClient(self.config)
            
            if name == "search_questions":
                return await self._handle_search_questions(arguments)
            elif name == "search_by_tags":
                return await self._handle_search_by_tags(arguments)
            elif name == "get_question":
                return await self._handle_get_question(arguments)
            elif name == "get_question_with_answers":
                return await self._handle_get_question_with_answers(arguments)
            elif name == "get_rate_limit_status":
                return await self._handle_get_rate_limit_status(arguments)
            elif name == "get_authentication_status":
                return await self._handle_get_authentication_status(arguments)
            elif name == "get_queue_status":
                return await self._handle_get_queue_status(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Handle resource reading."""
            logger.info(f"Resource requested: {uri}")
            
            if uri == "stackoverflow://status":
                status = {
                    "server": "stackoverflow-mcp",
                    "version": "0.1.0",
                    "status": "running",
                    "config": {
                        "host": self.config.host,
                        "port": self.config.port,
                        "api_key_configured": bool(self.config.stackoverflow_api_key),
                        "max_requests_per_minute": self.config.max_requests_per_minute
                    }
                }
                return str(status)
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def _ensure_client(self) -> None:
        """Ensure the StackOverflow client is initialized and optionally validate authentication."""
        if self.stackoverflow_client is None:
            logger.info("Initializing StackOverflow client")
            self.stackoverflow_client = StackOverflowClient(self.config)
            
            # Validate API key if configured
            if self.config.stackoverflow_api_key:
                logger.info("API key configured, validating authentication...")
                try:
                    is_valid = await self.stackoverflow_client.validate_api_key()
                    if is_valid:
                        logger.info("API authentication successful")
                    else:
                        logger.warning("API authentication failed - continuing with unauthenticated access")
                except Exception as e:
                    logger.warning(f"API authentication validation error: {e} - continuing with unauthenticated access")
            else:
                logger.info("No API key configured - using unauthenticated access (lower rate limits apply)")
    
    async def _handle_search_questions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_questions tool call."""
        try:
            await self._ensure_client()
            
            query = arguments.get("query", "").strip()
            if not query:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "Search query cannot be empty",
                    category="validation"
                )
            
            page = arguments.get("page", 1)
            limit = arguments.get("limit", 10)
            sort = arguments.get("sort", "relevance")
            
            # Validate parameters
            if not isinstance(page, int) or page < 1:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "Page must be a positive integer",
                    category="validation"
                )
            
            if not isinstance(limit, int) or limit < 1 or limit > 100:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "Limit must be between 1 and 100",
                    category="validation"
                )
            
            # Perform search
            result = await self.stackoverflow_client.search_questions(
                query=query,
                page=page,
                page_size=limit,
                sort=sort
            )
            
            # Check for API errors
            error_response = self.stackoverflow_client.error_handler.handle_api_error(result)
            if error_response:
                return error_response
            
            # Validate and clean response
            result = self.stackoverflow_client.content_formatter.validate_and_clean_response(result)
            
            questions = result.get("items", [])
            total = result.get("total", 0)
            
            if not questions:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🔍 No questions found for query: '{query}'"
                        }
                    ]
                }
            
            # Format results with enhanced formatting
            formatted_results = [f"📊 **Found {total} questions for '{query}'**\n"]
            
            for i, question in enumerate(questions, 1):
                title = question.get("title", "No title")
                question_id = question.get("question_id", "Unknown")
                score = question.get("score", 0)
                view_count = question.get("view_count", 0)
                answer_count = question.get("answer_count", 0)
                tags = question.get("tags", [])
                link = question.get("link", "")
                
                # Enhanced formatting with emojis and better structure
                score_icon = "🔥" if score >= 10 else "👍" if score >= 5 else "➡️"
                answer_icon = "✅" if answer_count > 0 else "❓"
                
                formatted_results.append(
                    f"\n## {i}. {title}\n"
                    f"**ID:** {question_id} | **Score:** {score_icon} {score} | "
                    f"**Views:** 👀 {view_count:,} | **Answers:** {answer_icon} {answer_count}\n"
                    f"**Tags:** {', '.join(f'`{tag}`' for tag in tags[:5])}\n"
                    f"**Link:** {link}\n"
                )
            
            # Add pagination info if relevant
            if total > limit:
                remaining = total - (page * limit)
                if remaining > 0:
                    formatted_results.append(f"\n💡 *Showing page {page} of results. {remaining} more questions available.*")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(formatted_results)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in search_questions: {e}")
            return self.stackoverflow_client.error_handler.create_error_response(
                f"Failed to search questions: {str(e)}",
                category="internal",
                details={"query": arguments.get("query"), "error": str(e)}
            )
    
    async def _handle_search_by_tags(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_by_tags tool call."""
        try:
            await self._ensure_client()
            
            tags = arguments.get("tags", [])
            if not tags or not any(str(tag).strip() for tag in tags):
                return self.stackoverflow_client.error_handler.create_error_response(
                    "Tags cannot be empty",
                    category="validation"
                )
            
            # Clean and validate tags
            clean_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
            if not clean_tags:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "At least one valid tag is required",
                    category="validation"
                )
            
            page = arguments.get("page", 1)
            limit = arguments.get("limit", 10)
            sort = arguments.get("sort", "activity")
            
            # Validate parameters
            if not isinstance(page, int) or page < 1:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "Page must be a positive integer",
                    category="validation"
                )
            
            if not isinstance(limit, int) or limit < 1 or limit > 100:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "Limit must be between 1 and 100",
                    category="validation"
                )
            
            # Perform search
            result = await self.stackoverflow_client.search_by_tags(
                tags=clean_tags,
                page=page,
                page_size=limit,
                sort=sort
            )
            
            # Check for API errors
            error_response = self.stackoverflow_client.error_handler.handle_api_error(result)
            if error_response:
                return error_response
            
            # Validate and clean response
            result = self.stackoverflow_client.content_formatter.validate_and_clean_response(result)
            
            questions = result.get("items", [])
            total = result.get("total", 0)
            
            if not questions:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🏷️ No questions found for tags: {', '.join(clean_tags)}"
                        }
                    ]
                }
            
            # Format results with enhanced formatting
            tag_display = ', '.join(f'`{tag}`' for tag in clean_tags)
            formatted_results = [f"🏷️ **Found {total} questions for tags: {tag_display}**\n"]
            
            for i, question in enumerate(questions, 1):
                title = question.get("title", "No title")
                question_id = question.get("question_id", "Unknown")
                score = question.get("score", 0)
                view_count = question.get("view_count", 0)
                answer_count = question.get("answer_count", 0)
                tags = question.get("tags", [])
                link = question.get("link", "")
                
                # Enhanced formatting
                score_icon = "🔥" if score >= 10 else "👍" if score >= 5 else "➡️"
                answer_icon = "✅" if answer_count > 0 else "❓"
                
                formatted_results.append(
                    f"\n## {i}. {title}\n"
                    f"**ID:** {question_id} | **Score:** {score_icon} {score} | "
                    f"**Views:** 👀 {view_count:,} | **Answers:** {answer_icon} {answer_count}\n"
                    f"**Tags:** {', '.join(f'`{tag}`' for tag in tags[:5])}\n"
                    f"**Link:** {link}\n"
                )
            
            # Add pagination info
            if total > limit:
                remaining = total - (page * limit)
                if remaining > 0:
                    formatted_results.append(f"\n💡 *Showing page {page} of results. {remaining} more questions available.*")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(formatted_results)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in search_by_tags: {e}")
            return self.stackoverflow_client.error_handler.create_error_response(
                f"Failed to search by tags: {str(e)}",
                category="internal",
                details={"tags": arguments.get("tags"), "error": str(e)}
            )
    
    async def _handle_get_question(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_question tool call."""
        try:
            await self._ensure_client()
            
            question_id = arguments.get("question_id")
            include_answers = arguments.get("include_answers", True)
            convert_to_markdown = arguments.get("convert_to_markdown", True)
            
            if not question_id:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "question_id is required",
                    category="validation"
                )
            
            # Validate question_id
            try:
                question_id = int(question_id)
                if question_id <= 0:
                    raise ValueError("Invalid question ID")
            except (ValueError, TypeError):
                return self.stackoverflow_client.error_handler.create_error_response(
                    "question_id must be a positive integer",
                    category="validation"
                )
            
            # Get question details
            question = await self.stackoverflow_client.get_question_details(
                question_id, 
                include_answers=include_answers
            )
            
            # Check for API errors
            error_response = self.stackoverflow_client.error_handler.handle_api_error(question)
            if error_response:
                return error_response
            
            # Format question details with enhanced formatting
            title = question.get("title", "No title")
            body = question.get("body", "No body available")
            score = question.get("score", 0)
            view_count = question.get("view_count", 0)
            answer_count = question.get("answer_count", 0)
            tags = question.get("tags", [])
            link = question.get("link", "")
            
            # Convert HTML to markdown if requested
            if convert_to_markdown and body:
                body = self.stackoverflow_client._convert_html_to_markdown(body)
            
            # Enhanced formatting with icons and better structure
            score_icon = "🔥" if score >= 10 else "👍" if score >= 5 else "➡️"
            view_icon = "👀"
            answer_icon = "✅" if answer_count > 0 else "❓"
            
            formatted_result = (
                f"# 📋 {title}\n\n"
                f"**Question ID:** {question_id}\n"
                f"**Score:** {score_icon} {score} | **Views:** {view_icon} {view_count:,} | **Answers:** {answer_icon} {answer_count}\n"
                f"**Tags:** {', '.join(f'`{tag}`' for tag in tags)}\n"
                f"**Link:** {link}\n\n"
                f"## 📝 Question Content\n\n{body}"
            )
            
            # Add answer summary if requested and available
            if include_answers and question.get("answers"):
                answers = question["answers"]
                formatted_result += f"\n\n## 💬 Answers ({len(answers)} total)\n"
                
                for i, answer in enumerate(answers[:3], 1):  # Show first 3 answers
                    answer_score = answer.get("score", 0)
                    is_accepted = answer.get("is_accepted", False)
                    accepted_marker = " ✅ **ACCEPTED**" if is_accepted else ""
                    score_marker = "🔥" if answer_score >= 10 else "👍" if answer_score >= 5 else "➡️"
                    
                    formatted_result += f"\n### Answer {i}{accepted_marker}\n"
                    formatted_result += f"**Score:** {score_marker} {answer_score}\n"
                
                if len(answers) > 3:
                    formatted_result += f"\n*... and {len(answers) - 3} more answer(s)*\n"
                
                formatted_result += "\n💡 *Use `get_question_with_answers` for full answer details.*"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": formatted_result
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in get_question: {e}")
            return self.stackoverflow_client.error_handler.create_error_response(
                f"Failed to get question details: {str(e)}",
                category="internal",
                details={"question_id": arguments.get("question_id"), "error": str(e)}
            )
    
    async def _handle_get_question_with_answers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_question_with_answers tool call."""
        try:
            await self._ensure_client()
            
            question_id = arguments.get("question_id")
            max_answers = arguments.get("max_answers", 5)
            convert_to_markdown = arguments.get("convert_to_markdown", True)
            
            if not question_id:
                return self.stackoverflow_client.error_handler.create_error_response(
                    "question_id is required",
                    category="validation"
                )
            
            # Validate question_id
            try:
                question_id = int(question_id)
                if question_id <= 0:
                    raise ValueError("Invalid question ID")
            except (ValueError, TypeError):
                return self.stackoverflow_client.error_handler.create_error_response(
                    "question_id must be a positive integer",
                    category="validation"
                )
            
            # Get question details with answers
            question = await self.stackoverflow_client.get_question_details(question_id, include_answers=True)
            
            # Check for API errors
            error_response = self.stackoverflow_client.error_handler.handle_api_error(question)
            if error_response:
                return error_response
            
            # Format question details
            title = question.get("title", "No title")
            body = question.get("body", "No body available")
            score = question.get("score", 0)
            view_count = question.get("view_count", 0)
            answer_count = question.get("answer_count", 0)
            tags = question.get("tags", [])
            link = question.get("link", "")
            creation_date = question.get("creation_date", 0)
            owner = question.get("owner", {})
            
            # Convert HTML to markdown if requested
            if convert_to_markdown and body:
                body = self.stackoverflow_client._convert_html_to_markdown(body)
            
            # Format creation date
            import datetime
            created_date = datetime.datetime.fromtimestamp(creation_date).strftime("%Y-%m-%d %H:%M:%S") if creation_date else "Unknown"
            author_name = owner.get("display_name", "Unknown")
            
            formatted_result = [
                f"# {title}",
                f"**Question ID:** {question_id}",
                f"**Score:** {score} | **Views:** {view_count:,} | **Answers:** {answer_count}",
                f"**Tags:** {', '.join(tags)}",
                f"**Author:** {author_name}",
                f"**Created:** {created_date}",
                f"**Link:** {link}",
                "",
                "## Question",
                body,
                ""
            ]
            
            # Add answers
            answers = question.get("answers", [])
            if answers:
                formatted_result.append("## Answers")
                formatted_result.append("")
                
                # Limit number of answers
                limited_answers = answers[:max_answers]
                
                for i, answer in enumerate(limited_answers, 1):
                    answer_body = answer.get("body", "No content")
                    answer_score = answer.get("score", 0)
                    is_accepted = answer.get("is_accepted", False)
                    answer_owner = answer.get("owner", {})
                    answer_author = answer_owner.get("display_name", "Unknown")
                    answer_creation = answer.get("creation_date", 0)
                    answer_date = datetime.datetime.fromtimestamp(answer_creation).strftime("%Y-%m-%d %H:%M:%S") if answer_creation else "Unknown"
                    
                    # Convert HTML to markdown if requested
                    if convert_to_markdown and answer_body:
                        answer_body = self.stackoverflow_client._convert_html_to_markdown(answer_body)
                    
                    # Format answer header
                    accepted_marker = " ✅ **ACCEPTED**" if is_accepted else ""
                    formatted_result.extend([
                        f"### Answer {i}{accepted_marker}",
                        f"**Score:** {answer_score} | **Author:** {answer_author} | **Date:** {answer_date}",
                        "",
                        answer_body,
                        "",
                        "---",
                        ""
                    ])
                
                # Note if there are more answers
                if len(answers) > max_answers:
                    remaining = len(answers) - max_answers
                    formatted_result.append(f"*Note: {remaining} more answer(s) available. Use a larger max_answers value to see them.*")
            else:
                formatted_result.append("*No answers available for this question.*")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(formatted_result)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in get_question_with_answers: {e}")
            return self.stackoverflow_client.error_handler.create_error_response(
                f"Failed to get question details: {str(e)}",
                category="internal",
                details={"question_id": arguments.get("question_id"), "error": str(e)}
            )
    
    async def _handle_get_rate_limit_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_rate_limit_status tool call."""
        try:
            await self._ensure_client()
            
            # Get rate limit status from client
            status = self.stackoverflow_client.get_rate_limit_status()
            
            # Format status information
            result_lines = [
                "# StackOverflow API Rate Limit Status",
                "",
                f"**Rate Limited:** {'Yes' if status['is_rate_limited'] else 'No'}",
                f"**Current Backoff:** {status['current_backoff']:.1f} seconds"
            ]
            
            if status['is_rate_limited']:
                import time
                wait_time = status['backoff_until'] - time.time()
                result_lines.append(f"**Wait Time:** {max(0, wait_time):.1f} seconds")
            
            if status['remaining_requests'] is not None:
                result_lines.extend([
                    f"**Remaining Requests:** {status['remaining_requests']}",
                ])
            
            if status['reset_time'] is not None:
                import datetime
                reset_dt = datetime.datetime.fromtimestamp(status['reset_time'])
                result_lines.append(f"**Quota Resets:** {reset_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            result_lines.extend([
                "",
                "## Client-Side Rate Limiting",
                f"**Requests This Window:** {status['requests_this_window']}",
                f"**Max Requests Per Minute:** {self.config.max_requests_per_minute}",
                f"**Request Delay:** {self.config.retry_delay} seconds"
            ])
            
            # Add window timing
            import time
            window_elapsed = time.time() - status['window_start']
            window_remaining = 60 - window_elapsed
            result_lines.extend([
                f"**Window Elapsed:** {window_elapsed:.1f} seconds",
                f"**Window Remaining:** {max(0, window_remaining):.1f} seconds"
            ])
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(result_lines)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return self.stackoverflow_client.error_handler.create_error_response(
                f"Failed to get rate limit status: {str(e)}",
                category="internal",
                details={}
            )
    
    async def _handle_get_authentication_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_authentication_status tool call."""
        try:
            await self._ensure_client()
            
            # Get authentication status from client
            status = self.stackoverflow_client.get_authentication_status()
            
            # Format status information
            result_lines = [
                "# StackOverflow API Authentication Status",
                "",
                f"**API Key Configured:** {'Yes' if status['api_key_configured'] else 'No'}",
                f"**Authentication Tested:** {'Yes' if status['authentication_tested'] else 'No'}",
                f"**Is Authenticated:** {'Yes' if status['is_authenticated'] else 'No'}"
            ]
            
            if status['api_key_valid'] is not None:
                result_lines.append(f"**API Key Valid:** {'Yes' if status['api_key_valid'] else 'No'}")
            else:
                result_lines.append("**API Key Valid:** Unknown (not tested)")
            
            if status['authentication_error']:
                result_lines.extend([
                    "",
                    "## Authentication Error",
                    f"**Error:** {status['authentication_error']}"
                ])
            
            if status['daily_quota'] is not None or status['daily_quota_remaining'] is not None:
                result_lines.extend([
                    "",
                    "## API Quota Information"
                ])
                
                if status['daily_quota'] is not None and status['daily_quota_remaining'] is not None:
                    quota_used = status['daily_quota'] - status['daily_quota_remaining']
                    quota_percent = (quota_used / status['daily_quota']) * 100 if status['daily_quota'] > 0 else 0
                    result_lines.extend([
                        f"**Daily Quota:** {status['daily_quota']} requests",
                        f"**Remaining:** {status['daily_quota_remaining']} requests",
                        f"**Used:** {quota_used} requests ({quota_percent:.1f}%)"
                    ])
                elif status['daily_quota_remaining'] is not None:
                    result_lines.append(f"**Remaining Quota:** {status['daily_quota_remaining']} requests")
                elif status['daily_quota'] is not None:
                    result_lines.append(f"**Daily Quota:** {status['daily_quota']} requests")
            
            if status['last_validation_time']:
                import datetime
                validation_dt = datetime.datetime.fromtimestamp(status['last_validation_time'])
                result_lines.extend([
                    "",
                    f"**Last Validation:** {validation_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                ])
            
            # Add configuration guidance
            if not status['api_key_configured']:
                result_lines.extend([
                    "",
                    "## Configuration Guide",
                    "To configure API authentication:",
                    "1. Get an API key from StackOverflow: https://stackapps.com/apps/oauth/register",
                    "2. Set the environment variable: `export STACKOVERFLOW_API_KEY=your_key_here`",
                    "3. Or add it to your .env file: `STACKOVERFLOW_API_KEY=your_key_here`",
                    "4. Restart the MCP server",
                    "",
                    "**Benefits of API authentication:**",
                    "- Higher rate limits (10,000 requests/day vs 300/day)",
                    "- More reliable service during peak usage",
                    "- Access to additional API features"
                ])
            elif not status['is_authenticated']:
                result_lines.extend([
                    "",
                    "## Troubleshooting",
                    "API key is configured but authentication failed:",
                    "1. Verify your API key is correct",
                    "2. Check that the key hasn't expired",
                    "3. Ensure network connectivity to api.stackexchange.com",
                    "4. Try regenerating your API key if issues persist"
                ])
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(result_lines)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting authentication status: {e}")
            return self.stackoverflow_client.error_handler.create_error_response(
                f"Failed to get authentication status: {str(e)}",
                category="internal",
                details={}
            )
    
    async def _handle_get_queue_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_queue_status tool call."""
        try:
            await self._ensure_client()
            
            # Get queue status from client
            status = self.stackoverflow_client.get_queue_status()
            
            # Format status information
            result_lines = [
                "# StackOverflow MCP Request Queue Status",
                "",
                "## Queue Information",
                f"**Queued Requests:** {status['queue']['queued']}",
                f"**Processing Requests:** {status['queue']['processing']}",
                f"**Completed Requests:** {status['queue']['completed']}",
                f"**Max Concurrent:** {status['queue']['max_concurrent']}",
                f"**Worker Running:** {'Yes' if status['queue']['worker_running'] else 'No'}",
                "",
                "## Cache Statistics",
                f"**Total Entries:** {status['cache']['total_entries']}",
                f"**Valid Entries:** {status['cache']['valid_entries']}",
                f"**Max Size:** {status['cache']['max_size']}",
                f"**TTL:** {status['cache']['ttl_seconds']} seconds",
                "",
                "## Auto-Switching Configuration",
                f"**Auto-Switch Enabled:** {'Yes' if status['auto_switch_enabled'] else 'No'}",
                f"**Current Access Mode:** {status['current_access_mode']}"
            ]
            
            # Add performance metrics if available
            queue_stats = status['queue']
            if queue_stats['completed'] > 0:
                total_requests = queue_stats['queued'] + queue_stats['processing'] + queue_stats['completed']
                completion_rate = (queue_stats['completed'] / total_requests) * 100 if total_requests > 0 else 0
                
                result_lines.extend([
                    "",
                    "## Performance Metrics",
                    f"**Total Requests Processed:** {total_requests}",
                    f"**Completion Rate:** {completion_rate:.1f}%"
                ])
            
            # Add cache performance if available
            cache_stats = status['cache']
            if cache_stats['total_entries'] > 0:
                cache_hit_potential = (cache_stats['valid_entries'] / cache_stats['total_entries']) * 100
                result_lines.extend([
                    f"**Cache Efficiency:** {cache_hit_potential:.1f}% valid entries"
                ])
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(result_lines)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return self.stackoverflow_client.error_handler.create_error_response(
                f"Failed to get queue status: {str(e)}",
                category="internal",
                details={}
            )
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self) -> None:
        """Start the MCP server."""
        logger.info(f"Starting StackOverflow MCP server with stdio transport")
        
        self._setup_signal_handlers()
        
        try:
            import sys
            from mcp.server.stdio import stdio_server
            
            # Start the MCP server using stdio transport
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, 
                    write_stream, 
                    self.server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            # Clean up client
            if self.stackoverflow_client:
                await self.stackoverflow_client.__aexit__(None, None, None)
    
    async def stop(self) -> None:
        """Stop the MCP server gracefully."""
        logger.info("Stopping StackOverflow MCP server...")
        self._shutdown_event.set()
        
        # Clean up client
        if self.stackoverflow_client:
            await self.stackoverflow_client.__aexit__(None, None, None)
        
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait() 