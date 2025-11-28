"""
Tests for MCP Router
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fiml.core.models import (
    AnalysisDepth,
    CachedData,
    DataLineage,
    Market,
    SearchByCoinResponse,
    SearchBySymbolResponse,
    TaskInfo,
    TaskStatus,
)
from fiml.mcp.router import MCP_TOOLS
from fiml.server import app

client = TestClient(app)


def test_list_tools():
    """Test listing available tools"""
    response = client.get("/mcp/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) == len(MCP_TOOLS)
    assert data["tools"][0]["name"] == "search-by-symbol"


@pytest.mark.asyncio
async def test_call_tool_search_by_symbol():
    """Test calling search-by-symbol tool"""

    # Mock response object
    mock_response = SearchBySymbolResponse(
        symbol="AAPL",
        name="Apple Inc.",
        exchange="NASDAQ",
        market="US",
        currency="USD",
        cached=CachedData(
            price=150.0,
            change=2.5,
            change_percent=1.6,
            as_of=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            source="test",
            ttl=300,
            confidence=1.0,
        ),
        task=TaskInfo(
            id="task-123",
            type="equity_analysis",
            status=TaskStatus.PENDING,
            resource_url="mcp://task/task-123",
            estimated_completion=datetime.now(timezone.utc),
            progress=0.0,
        ),
        disclaimer="Test disclaimer",
        data_lineage=DataLineage(
            providers=["test"],
            arbitration_score=1.0,
            conflict_resolved=False,
            source_count=1,
        ),
    )

    with patch("fiml.mcp.router.search_by_symbol", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "search-by-symbol",
                "arguments": {
                    "symbol": "AAPL",
                    "market": "US",
                    "depth": "standard",
                    "language": "en"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert not data["isError"]
        assert len(data["content"]) == 1
        assert "AAPL" in data["content"][0]["text"]

        mock_search.assert_called_once()
        call_args = mock_search.call_args[1]
        assert call_args["symbol"] == "AAPL"
        assert call_args["market"] == Market.US
        assert call_args["depth"] == AnalysisDepth.STANDARD


@pytest.mark.asyncio
async def test_call_tool_search_by_coin():
    """Test calling search-by-coin tool"""

    mock_response = SearchByCoinResponse(
        symbol="BTC",
        name="Bitcoin",
        pair="BTC/USDT",
        exchange="binance",
        cached=CachedData(
            price=50000.0,
            change=100.0,
            change_percent=0.2,
            as_of=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            source="test",
            ttl=300,
            confidence=1.0,
        ),
        crypto_metrics={},
        task=TaskInfo(
            id="task-456",
            type="crypto_analysis",
            status=TaskStatus.PENDING,
            resource_url="mcp://task/task-456",
            estimated_completion=datetime.now(timezone.utc),
            progress=0.0,
        ),
        disclaimer="Test disclaimer",
        data_lineage=DataLineage(
            providers=["test"],
            arbitration_score=1.0,
            conflict_resolved=False,
            source_count=1,
        ),
    )

    with patch("fiml.mcp.router.search_by_coin", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "search-by-coin",
                "arguments": {
                    "symbol": "BTC",
                    "exchange": "binance",
                    "pair": "USDT"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert not data["isError"]
        assert "BTC" in data["content"][0]["text"]

        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_call_tool_get_task_status():
    """Test calling get-task-status tool"""

    mock_result = {"status": "completed", "progress": 100}

    with patch("fiml.mcp.router.get_task_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = mock_result

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "get-task-status",
                "arguments": {"taskId": "task-123"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert not data["isError"]
        assert "completed" in data["content"][0]["text"]

        mock_status.assert_called_once_with(task_id="task-123", stream=False)


@pytest.mark.asyncio
async def test_call_tool_execute_fk_dsl():
    """Test calling execute-fk-dsl tool"""

    mock_result = {"result": "success"}

    with patch("fiml.mcp.router.execute_fk_dsl", new_callable=AsyncMock) as mock_dsl:
        mock_dsl.return_value = mock_result

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "execute-fk-dsl",
                "arguments": {"query": "GET PRICE AAPL"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert not data["isError"]

        mock_dsl.assert_called_once_with(query="GET PRICE AAPL", async_execution=True)


@pytest.mark.asyncio
async def test_call_tool_session_management():
    """Test session management tools"""

    # create-analysis-session
    with patch("fiml.mcp.router.create_analysis_session", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {"sessionId": "sess-1"}

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "create-analysis-session",
                "arguments": {
                    "assets": ["AAPL"],
                    "sessionType": "equity"
                }
            }
        )
        assert response.status_code == 200
        assert "sess-1" in response.json()["content"][0]["text"]

    # get-session-info
    with patch("fiml.mcp.router.get_session_info", new_callable=AsyncMock) as mock_info:
        mock_info.return_value = {"id": "sess-1"}

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "get-session-info",
                "arguments": {"sessionId": "sess-1"}
            }
        )
        assert response.status_code == 200

    # list-sessions
    with patch("fiml.mcp.router.list_sessions", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [{"id": "sess-1"}]

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "list-sessions",
                "arguments": {"userId": "user-1"}
            }
        )
        assert response.status_code == 200

    # extend-session
    with patch("fiml.mcp.router.extend_session", new_callable=AsyncMock) as mock_extend:
        mock_extend.return_value = {"success": True}

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "extend-session",
                "arguments": {"sessionId": "sess-1"}
            }
        )
        assert response.status_code == 200

    # get-session-analytics
    with patch("fiml.mcp.router.get_session_analytics", new_callable=AsyncMock) as mock_analytics:
        mock_analytics.return_value = {"count": 10}

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "get-session-analytics",
                "arguments": {"userId": "user-1"}
            }
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_call_tool_warm_cache():
    """Test calling warm-cache tool"""

    mock_result = {"warmed": ["AAPL"]}

    # Need to mock the import inside the function
    with patch("fiml.cache.warming.cache_warmer.warm_cache_batch", new_callable=AsyncMock) as mock_warm:
        mock_warm.return_value = mock_result

        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "warm-cache",
                "arguments": {"symbols": ["AAPL"]}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert not data["isError"]
        assert "AAPL" in data["content"][0]["text"]


def test_call_tool_unknown():
    """Test calling unknown tool"""
    response = client.post(
        "/mcp/tools/call",
        json={
            "name": "unknown-tool",
            "arguments": {}
        }
    )

    assert response.status_code == 200  # MCP protocol returns 200 with isError=True
    data = response.json()
    assert data["isError"] is True
    assert "Tool not found" in data["content"][0]["text"]


def test_call_tool_exception():
    """Test exception handling during tool call"""

    with patch("fiml.mcp.router.search_by_symbol", side_effect=Exception("Test Error")):
        response = client.post(
            "/mcp/tools/call",
            json={
                "name": "search-by-symbol",
                "arguments": {"symbol": "AAPL"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is True
        assert "Test Error" in data["content"][0]["text"]
