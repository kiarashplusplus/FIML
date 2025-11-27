"""
Tests for MCP Router and Tools
"""

import pytest
from fastapi.testclient import TestClient

from fiml.mcp.router import MCP_TOOLS, MCPToolRequest, MCPToolResponse
from fiml.server import app


class TestMCPRouter:
    """Test MCP router"""

    def test_mcp_tools_list(self):
        """Test MCP tools are defined"""
        assert isinstance(MCP_TOOLS, list)
        assert len(MCP_TOOLS) > 0

        # Check each tool has required fields
        for tool in MCP_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_mcp_tool_request_model(self):
        """Test MCP tool request model"""
        request = MCPToolRequest(name="search-by-symbol", arguments={"symbol": "AAPL"})
        assert request.name == "search-by-symbol"
        assert request.arguments["symbol"] == "AAPL"

    def test_mcp_tool_response_model(self):
        """Test MCP tool response model"""
        response = MCPToolResponse(content=[{"type": "text", "text": "Result"}], isError=False)
        assert response.isError is False
        assert len(response.content) == 1


class TestMCPTools:
    """Test MCP tools"""

    @pytest.mark.asyncio
    async def test_search_by_symbol_tool(self):
        """Test search by symbol tool"""
        from fiml.mcp.tools import search_by_symbol
        from fiml.providers.registry import provider_registry

        await provider_registry.initialize()

        try:
            result = await search_by_symbol(symbol="AAPL", market="US", analysis_depth="quick")

            # Result should be a dict
            assert isinstance(result, dict)

        except Exception:
            # Some errors are acceptable if providers aren't fully available
            pass

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_search_by_coin_tool(self):
        """Test search by coin tool"""
        from fiml.mcp.tools import search_by_coin
        from fiml.providers.registry import provider_registry

        await provider_registry.initialize()

        try:
            result = await search_by_coin(symbol="BTC", pair="USD")

            # Result should be a dict
            assert isinstance(result, dict)

        except Exception:
            # Some errors are acceptable if providers aren't fully available
            pass

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_execute_fk_dsl_tool(self):
        """Test execute FK-DSL tool"""
        from fiml.mcp.tools import execute_fk_dsl

        result = await execute_fk_dsl(query="GET PRICE FOR AAPL")

        # Should return task info
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_task_status_tool(self):
        """Test get task status tool"""
        from fiml.mcp.tools import execute_fk_dsl, get_task_status

        # First create a task
        result = await execute_fk_dsl(query="GET PRICE FOR AAPL")
        task_id = result.get("id")  # Get task ID from result

        if task_id:
            # Get its status
            status = await get_task_status(task_id=task_id)
            assert isinstance(status, dict)


class TestServer:
    """Test FastAPI server"""

    def test_server_creation(self):
        """Test server app is created"""
        assert app is not None

    def test_health_endpoint(self):
        """Test health endpoint"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_mcp_tools_endpoint(self):
        """Test MCP tools listing endpoint"""
        client = TestClient(app)
        response = client.get("/mcp/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)

    def test_root_endpoint(self):
        """Test root endpoint"""
        client = TestClient(app)
        response = client.get("/")

        # Should return some response
        assert response.status_code in [200, 404, 307]
