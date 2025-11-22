"""
MCP Protocol Router and Tool Handlers
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fiml.core.logging import get_logger
from fiml.core.models import AnalysisDepth, Market
from fiml.mcp.tools import (
    execute_fk_dsl,
    get_task_status,
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

    content: list[Dict[str, Any]]
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
            result = await search_by_symbol(
                symbol=request.arguments["symbol"],
                market=Market(request.arguments.get("market", "US")),
                depth=AnalysisDepth(request.arguments.get("depth", "standard")),
                language=request.arguments.get("language", "en"),
            )
            return MCPToolResponse(content=[{"type": "text", "text": result.model_dump_json()}])

        elif request.name == "search-by-coin":
            result = await search_by_coin(
                symbol=request.arguments["symbol"],
                exchange=request.arguments.get("exchange", "binance"),
                pair=request.arguments.get("pair", "USDT"),
                depth=AnalysisDepth(request.arguments.get("depth", "standard")),
                language=request.arguments.get("language", "en"),
            )
            return MCPToolResponse(content=[{"type": "text", "text": result.model_dump_json()}])

        elif request.name == "get-task-status":
            result = await get_task_status(
                task_id=request.arguments["taskId"],
                stream=request.arguments.get("stream", False),
            )
            return MCPToolResponse(content=[{"type": "text", "text": result.model_dump_json()}])

        elif request.name == "execute-fk-dsl":
            result = await execute_fk_dsl(
                query=request.arguments["query"],
                async_execution=request.arguments.get("async", True),
            )
            return MCPToolResponse(content=[{"type": "text", "text": result.model_dump_json()}])

        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {request.name}")

    except Exception as e:
        logger.exception("Error executing MCP tool", tool=request.name, error=str(e))
        return MCPToolResponse(
            content=[{"type": "text", "text": f"Error: {str(e)}"}], isError=True
        )
