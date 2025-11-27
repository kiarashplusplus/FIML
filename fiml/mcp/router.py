"""
MCP Protocol Router and Tool Handlers
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fiml.core.logging import get_logger
from fiml.core.models import AnalysisDepth, Market
from fiml.mcp.tools import (
    create_analysis_session,
    execute_fk_dsl,
    extend_session,
    get_session_analytics,
    get_session_info,
    get_task_status,
    list_sessions,
    search_by_coin,
    search_by_symbol,
)

logger = get_logger(__name__)

mcp_router = APIRouter()


class MCPToolRequest(BaseModel):
    """MCP tool request schema"""

    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolResponse(BaseModel):
    """MCP tool response schema"""

    content: List[Dict[str, Any]]
    isError: bool = Field(default=False)


# Tool Schemas for MCP Discovery
MCP_TOOLS = [
    {
        "name": "search-by-symbol",
        "description": "Search for a stock by symbol with instant cached data and async deep analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., TSLA, AAPL)",
                },
                "market": {
                    "type": "string",
                    "description": "Market/exchange (US, UK, JP, etc.)",
                    "default": "US",
                },
                "depth": {
                    "type": "string",
                    "enum": ["quick", "standard", "deep"],
                    "description": "Analysis depth",
                    "default": "standard",
                },
                "language": {
                    "type": "string",
                    "description": "Response language (en, ja, zh, es, fr, de)",
                    "default": "en",
                },
                "sessionId": {
                    "type": "string",
                    "description": "Optional session ID to track query context",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "search-by-coin",
        "description": "Search for cryptocurrency with instant cached data and async deep analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Crypto symbol (e.g., BTC, ETH, SOL)",
                },
                "exchange": {
                    "type": "string",
                    "description": "Preferred exchange (binance, coinbase, kraken, etc.)",
                    "default": "binance",
                },
                "pair": {
                    "type": "string",
                    "description": "Trading pair (e.g., USDT, USD, EUR)",
                    "default": "USDT",
                },
                "depth": {
                    "type": "string",
                    "enum": ["quick", "standard", "deep"],
                    "default": "standard",
                },
                "language": {
                    "type": "string",
                    "default": "en",
                },
                "sessionId": {
                    "type": "string",
                    "description": "Optional session ID to track query context",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get-task-status",
        "description": "Poll or stream updates for an async analysis task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "Task ID returned from search-by-symbol or search-by-coin",
                },
                "stream": {
                    "type": "boolean",
                    "description": "Stream updates via SSE instead of polling",
                    "default": False,
                },
            },
            "required": ["taskId"],
        },
    },
    {
        "name": "execute-fk-dsl",
        "description": "Execute a Financial Knowledge DSL query for complex multi-step analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "FK-DSL query string",
                },
                "async": {
                    "type": "boolean",
                    "description": "Execute asynchronously and return task ID",
                    "default": True,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "create-analysis-session",
        "description": "Create a new analysis session for tracking multi-query workflows",
        "inputSchema": {
            "type": "object",
            "properties": {
                "assets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of asset symbols to analyze in this session",
                },
                "sessionType": {
                    "type": "string",
                    "enum": ["equity", "crypto", "portfolio", "comparative", "macro"],
                    "description": "Type of analysis session",
                },
                "userId": {
                    "type": "string",
                    "description": "Optional user identifier",
                },
                "ttlHours": {
                    "type": "number",
                    "description": "Session time-to-live in hours (default 24)",
                    "default": 24,
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorizing the session",
                },
            },
            "required": ["assets", "sessionType"],
        },
    },
    {
        "name": "get-session-info",
        "description": "Get information about an existing session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sessionId": {
                    "type": "string",
                    "description": "Session UUID",
                },
            },
            "required": ["sessionId"],
        },
    },
    {
        "name": "list-sessions",
        "description": "List sessions for a user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "User identifier",
                },
                "includeArchived": {
                    "type": "boolean",
                    "description": "Include archived sessions",
                    "default": False,
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of sessions to return",
                    "default": 50,
                },
            },
            "required": ["userId"],
        },
    },
    {
        "name": "extend-session",
        "description": "Extend session expiration time",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sessionId": {
                    "type": "string",
                    "description": "Session UUID",
                },
                "hours": {
                    "type": "number",
                    "description": "Hours to extend by (default 24)",
                    "default": 24,
                },
            },
            "required": ["sessionId"],
        },
    },
    {
        "name": "get-session-analytics",
        "description": "Get session analytics and statistics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "Filter by user (optional)",
                },
                "sessionType": {
                    "type": "string",
                    "description": "Filter by session type (optional)",
                },
                "days": {
                    "type": "number",
                    "description": "Number of days to analyze (default 30)",
                    "default": 30,
                },
            },
        },
    },
]


@mcp_router.get("/tools")
async def list_tools() -> Dict[str, Any]:
    """List available MCP tools"""
    return {"tools": MCP_TOOLS}


@mcp_router.post("/tools/call")
async def call_tool(request: MCPToolRequest) -> MCPToolResponse:
    """Execute an MCP tool"""
    logger.info("MCP tool called", tool=request.name, arguments=request.arguments)

    try:
        if request.name == "search-by-symbol":
            symbol_result = await search_by_symbol(
                symbol=request.arguments["symbol"],
                market=Market(request.arguments.get("market", "US")),
                depth=AnalysisDepth(request.arguments.get("depth", "standard")),
                language=request.arguments.get("language", "en"),
                session_id=request.arguments.get("sessionId"),
            )
            return MCPToolResponse(
                content=[{"type": "text", "text": symbol_result.model_dump_json()}]
            )

        elif request.name == "search-by-coin":
            coin_result = await search_by_coin(
                symbol=request.arguments["symbol"],
                exchange=request.arguments.get("exchange", "binance"),
                pair=request.arguments.get("pair", "USDT"),
                depth=AnalysisDepth(request.arguments.get("depth", "standard")),
                language=request.arguments.get("language", "en"),
                session_id=request.arguments.get("sessionId"),
            )
            return MCPToolResponse(
                content=[{"type": "text", "text": coin_result.model_dump_json()}]
            )

        elif request.name == "get-task-status":
            task_result = await get_task_status(
                task_id=request.arguments["taskId"],
                stream=request.arguments.get("stream", False),
            )
            import json

            return MCPToolResponse(content=[{"type": "text", "text": json.dumps(task_result)}])

        elif request.name == "execute-fk-dsl":
            dsl_result = await execute_fk_dsl(
                query=request.arguments["query"],
                async_execution=request.arguments.get("async", True),
            )
            import json

            return MCPToolResponse(content=[{"type": "text", "text": json.dumps(dsl_result)}])

        elif request.name == "create-analysis-session":
            session_result = await create_analysis_session(
                assets=request.arguments["assets"],
                session_type=request.arguments["sessionType"],
                user_id=request.arguments.get("userId"),
                ttl_hours=request.arguments.get("ttlHours", 24),
                tags=request.arguments.get("tags"),
            )
            import json

            return MCPToolResponse(content=[{"type": "text", "text": json.dumps(session_result)}])

        elif request.name == "get-session-info":
            session_info = await get_session_info(
                session_id=request.arguments["sessionId"],
            )
            import json

            return MCPToolResponse(content=[{"type": "text", "text": json.dumps(session_info)}])

        elif request.name == "list-sessions":
            sessions_list = await list_sessions(
                user_id=request.arguments["userId"],
                include_archived=request.arguments.get("includeArchived", False),
                limit=request.arguments.get("limit", 50),
            )
            import json

            return MCPToolResponse(content=[{"type": "text", "text": json.dumps(sessions_list)}])

        elif request.name == "extend-session":
            extend_result = await extend_session(
                session_id=request.arguments["sessionId"],
                hours=request.arguments.get("hours", 24),
            )
            import json

            return MCPToolResponse(content=[{"type": "text", "text": json.dumps(extend_result)}])

        elif request.name == "get-session-analytics":
            analytics_result = await get_session_analytics(
                user_id=request.arguments.get("userId"),
                session_type=request.arguments.get("sessionType"),
                days=request.arguments.get("days", 30),
            )
            import json

            return MCPToolResponse(content=[{"type": "text", "text": json.dumps(analytics_result)}])

        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {request.name}")

    except Exception as e:
        logger.exception("Error executing MCP tool", tool=request.name, error=str(e))
        return MCPToolResponse(content=[{"type": "text", "text": f"Error: {str(e)}"}], isError=True)
