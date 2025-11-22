"""
Performance benchmarks for MCP Tools
"""

import pytest
from unittest.mock import AsyncMock, patch

from fiml.mcp.tools import (
    search_by_symbol,
    search_by_coin,
    get_provider_health,
    arbitrate_data_request,
)


class TestMCPBenchmarks:
    """Benchmarks for MCP tool operations"""

    @pytest.mark.asyncio
    async def test_search_by_symbol_tool(self, benchmark):
        """Benchmark search_by_symbol MCP tool"""
        
        async def run_search():
            # Mock the arbitration engine response
            with patch('fiml.mcp.tools.arbitration_engine') as mock_engine:
                mock_engine.arbitrate_request = AsyncMock(return_value={
                    "price": 150.50,
                    "volume": 1000000,
                    "provider": "MockProvider",
                })
                
                result = await search_by_symbol(
                    symbol="AAPL",
                    market="US",
                    depth="standard",
                    language="en",
                )
                return result
        
        result = await benchmark.pedantic(run_search, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_by_coin_tool(self, benchmark):
        """Benchmark search_by_coin MCP tool"""
        
        async def run_search():
            with patch('fiml.mcp.tools.arbitration_engine') as mock_engine:
                mock_engine.arbitrate_request = AsyncMock(return_value={
                    "price": 45000.00,
                    "volume": 1000000000,
                    "provider": "CCXTProvider",
                })
                
                result = await search_by_coin(
                    symbol="BTC",
                    exchange="binance",
                    pair="USDT",
                    depth="standard",
                )
                return result
        
        result = await benchmark.pedantic(run_search, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_provider_health_tool(self, benchmark):
        """Benchmark get_provider_health MCP tool"""
        
        async def get_health():
            with patch('fiml.mcp.tools.provider_registry') as mock_registry:
                mock_provider = AsyncMock()
                mock_provider.get_health = AsyncMock(return_value={
                    "provider_name": "MockProvider",
                    "is_available": True,
                    "uptime_percentage": 99.9,
                })
                mock_registry.get_provider = AsyncMock(return_value=mock_provider)
                
                result = await get_provider_health(provider_name="MockProvider")
                return result
        
        result = await benchmark.pedantic(get_health, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_arbitrate_data_tool(self, benchmark):
        """Benchmark arbitrate_data_request MCP tool"""
        
        async def arbitrate():
            with patch('fiml.mcp.tools.arbitration_engine') as mock_engine:
                mock_engine.arbitrate_request = AsyncMock(return_value={
                    "data": {"price": 150.50},
                    "provider": "MockProvider",
                    "confidence": 0.95,
                })
                
                result = await arbitrate_data_request(
                    symbol="AAPL",
                    asset_type="equity",
                    market="US",
                    data_type="price",
                )
                return result
        
        result = await benchmark.pedantic(arbitrate, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_mcp_tool_error_handling(self, benchmark):
        """Benchmark MCP tool error handling"""
        
        async def run_with_error():
            with patch('fiml.mcp.tools.arbitration_engine') as mock_engine:
                # Simulate provider error
                mock_engine.arbitrate_request = AsyncMock(
                    side_effect=Exception("Provider unavailable")
                )
                
                try:
                    result = await search_by_symbol(
                        symbol="INVALID",
                        market="US",
                        depth="standard",
                        language="en",
                    )
                    return result
                except Exception:
                    return None
        
        result = await benchmark.pedantic(run_with_error, rounds=10)
        # Error handling should be fast

    @pytest.mark.asyncio
    async def test_concurrent_mcp_requests(self, benchmark):
        """Benchmark concurrent MCP tool requests"""
        import asyncio
        
        async def concurrent_mcp():
            with patch('fiml.mcp.tools.arbitration_engine') as mock_engine:
                mock_engine.arbitrate_request = AsyncMock(return_value={
                    "price": 150.50,
                    "provider": "MockProvider",
                })
                
                tasks = [
                    search_by_symbol("AAPL", "US", "standard", "en"),
                    search_by_symbol("TSLA", "US", "standard", "en"),
                    search_by_symbol("MSFT", "US", "standard", "en"),
                    search_by_coin("BTC", "binance", "USDT", "standard"),
                    search_by_coin("ETH", "binance", "USDT", "standard"),
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
        
        results = await benchmark.pedantic(concurrent_mcp, rounds=5)
        assert len(results) == 5
