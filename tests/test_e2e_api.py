"""
End-to-End API Tests for FIML Server

These tests verify the complete API workflow including:
- Health checks
- MCP tool discovery
- Stock and crypto queries
- Error handling
- Response validation
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from fiml.server import app


class TestHealthEndpoints:
    """Test health and basic endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data
            assert "environment" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "FIML - Financial Intelligence Meta-Layer"
            assert "version" in data
            assert "docs" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
            response = await client.get("/metrics")
            assert response.status_code == 200
            # Metrics should be in Prometheus format
            assert b"python_info" in response.content or b"process_" in response.content


class TestMCPToolDiscovery:
    """Test MCP tool discovery endpoints"""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available MCP tools"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/mcp/tools")
            assert response.status_code == 200
            data = response.json()
            assert "tools" in data
            assert len(data["tools"]) > 0

            # Check for required tools
            tool_names = [tool["name"] for tool in data["tools"]]
            assert "search-by-symbol" in tool_names
            assert "search-by-coin" in tool_names
            assert "execute-fk-dsl" in tool_names
            assert "get-task-status" in tool_names

    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that all tools have proper schemas"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/mcp/tools")
            data = response.json()

            for tool in data["tools"]:
                assert "name" in tool
                assert "description" in tool
                assert "inputSchema" in tool
                assert "type" in tool["inputSchema"]
                assert "properties" in tool["inputSchema"]
                assert "required" in tool["inputSchema"]


class TestStockQueries:
    """Test stock query functionality"""

    @pytest.mark.asyncio
    async def test_search_by_symbol_basic(self):
        """Test basic stock search"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "name": "search-by-symbol",
                "arguments": {
                    "symbol": "AAPL",
                    "market": "US",
                    "depth": "quick"
                }
            }
            response = await client.post("/mcp/tools/call", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert "content" in data
            assert len(data["content"]) > 0
            assert data["isError"] is False

            # Parse the actual response
            result = json.loads(data["content"][0]["text"])
            assert result["symbol"] == "AAPL"
            assert "cached" in result
            assert "price" in result["cached"]
            assert "task" in result
            assert "disclaimer" in result

    @pytest.mark.asyncio
    async def test_search_by_symbol_different_stocks(self):
        """Test searching different stocks"""
        symbols = ["TSLA", "MSFT", "GOOGL"]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for symbol in symbols:
                payload = {
                    "name": "search-by-symbol",
                    "arguments": {
                        "symbol": symbol,
                        "market": "US",
                        "depth": "quick"
                    }
                }
                response = await client.post("/mcp/tools/call", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["isError"] is False

                result = json.loads(data["content"][0]["text"])
                assert result["symbol"] == symbol

    @pytest.mark.asyncio
    async def test_search_by_symbol_invalid_symbol(self):
        """Test handling of invalid stock symbol"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "name": "search-by-symbol",
                "arguments": {
                    "symbol": "INVALID_SYMBOL_XYZ",
                    "market": "US",
                    "depth": "quick"
                }
            }
            response = await client.post("/mcp/tools/call", json=payload)
            assert response.status_code == 200
            # Should handle gracefully, may return error in content


class TestCryptoQueries:
    """Test cryptocurrency query functionality"""

    @pytest.mark.asyncio
    async def test_search_by_coin_btc(self):
        """Test Bitcoin search"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "name": "search-by-coin",
                "arguments": {
                    "symbol": "BTC",
                    "exchange": "binance",
                    "depth": "quick"
                }
            }
            response = await client.post("/mcp/tools/call", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert "content" in data
            assert data["isError"] is False

            result = json.loads(data["content"][0]["text"])
            assert result["symbol"] == "BTC"
            assert "cached" in result

    @pytest.mark.asyncio
    async def test_search_by_coin_different_cryptos(self):
        """Test searching different cryptocurrencies"""
        symbols = ["BTC", "ETH", "SOL"]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for symbol in symbols:
                payload = {
                    "name": "search-by-coin",
                    "arguments": {
                        "symbol": symbol,
                        "exchange": "binance",
                        "depth": "quick"
                    }
                }
                response = await client.post("/mcp/tools/call", json=payload)
                assert response.status_code == 200


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test calling non-existent tool"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "name": "non-existent-tool",
                "arguments": {}
            }
            response = await client.post("/mcp/tools/call", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["isError"] is True

    @pytest.mark.asyncio
    async def test_missing_required_arguments(self):
        """Test calling tool without required arguments"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "name": "search-by-symbol",
                "arguments": {}  # Missing required 'symbol'
            }
            response = await client.post("/mcp/tools/call", json=payload)
            assert response.status_code == 200
            response.json()
            # Should handle missing arguments gracefully

    @pytest.mark.asyncio
    async def test_malformed_json(self):
        """Test handling of malformed JSON"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/mcp/tools/call",
                content=b"{invalid json}",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422  # Validation error


class TestDataQuality:
    """Test data quality and response structure"""

    @pytest.mark.asyncio
    async def test_response_has_required_fields(self):
        """Test that responses contain all required fields"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "name": "search-by-symbol",
                "arguments": {
                    "symbol": "AAPL",
                    "market": "US",
                    "depth": "quick"
                }
            }
            response = await client.post("/mcp/tools/call", json=payload)
            data = response.json()

            result = json.loads(data["content"][0]["text"])

            # Check required fields
            assert "symbol" in result
            assert "cached" in result
            assert "task" in result
            assert "disclaimer" in result
            assert "data_lineage" in result

            # Check cached data structure
            cached = result["cached"]
            assert "price" in cached
            assert "change" in cached
            assert "change_percent" in cached
            assert "as_of" in cached
            assert "source" in cached
            assert "confidence" in cached

            # Check task structure
            task = result["task"]
            assert "id" in task
            assert "status" in task
            assert "type" in task

    @pytest.mark.asyncio
    async def test_price_data_types(self):
        """Test that price data has correct types"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "name": "search-by-symbol",
                "arguments": {
                    "symbol": "AAPL",
                    "market": "US",
                    "depth": "quick"
                }
            }
            response = await client.post("/mcp/tools/call", json=payload)
            data = response.json()

            result = json.loads(data["content"][0]["text"])
            cached = result["cached"]

            # Verify data types
            assert isinstance(cached["price"], (int, float))
            assert isinstance(cached["change"], (int, float))
            assert isinstance(cached["change_percent"], (int, float))
            assert isinstance(cached["confidence"], (int, float))
            assert 0.0 <= cached["confidence"] <= 1.0


class TestConcurrency:
    """Test concurrent requests"""

    @pytest.mark.asyncio
    async def test_concurrent_stock_queries(self):
        """Test multiple concurrent stock queries"""
        import asyncio

        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async def query_symbol(symbol):
                payload = {
                    "name": "search-by-symbol",
                    "arguments": {
                        "symbol": symbol,
                        "market": "US",
                        "depth": "quick"
                    }
                }
                response = await client.post("/mcp/tools/call", json=payload)
                return response

            # Execute queries concurrently
            tasks = [query_symbol(symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["isError"] is False
