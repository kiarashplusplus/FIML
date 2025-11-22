"""
Performance benchmarks for Data Providers
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fiml.providers.mock_provider import MockProvider
from fiml.providers.base import ProviderConfig
from fiml.core.models import DataType


class TestProviderBenchmarks:
    """Benchmarks for provider operations"""

    @pytest.mark.asyncio
    async def test_mock_provider_get_price(self, benchmark, benchmark_asset):
        """Benchmark MockProvider price retrieval"""
        config = ProviderConfig(name="MockProvider", enabled=True)
        provider = MockProvider(config)
        
        async def get_price():
            return await provider.get_price(benchmark_asset)
        
        result = await benchmark.pedantic(get_price, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_mock_provider_get_historical(self, benchmark, benchmark_asset):
        """Benchmark MockProvider historical data retrieval"""
        config = ProviderConfig(name="MockProvider", enabled=True)
        provider = MockProvider(config)
        
        async def get_historical():
            return await provider.get_historical_data(
                benchmark_asset,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
            )
        
        result = await benchmark.pedantic(get_historical, rounds=5)
        assert result is not None

    @pytest.mark.asyncio
    async def test_provider_health_check(self, benchmark):
        """Benchmark provider health check"""
        config = ProviderConfig(name="MockProvider", enabled=True)
        provider = MockProvider(config)
        
        async def check_health():
            return await provider.get_health()
        
        result = await benchmark.pedantic(check_health, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_provider_supports_check(self, benchmark, benchmark_asset):
        """Benchmark provider supports_asset check"""
        config = ProviderConfig(name="MockProvider", enabled=True)
        provider = MockProvider(config)
        
        def check_support():
            return provider.supports_asset(benchmark_asset)
        
        result = benchmark(check_support)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_provider_data_type_support(self, benchmark):
        """Benchmark checking data type support"""
        config = ProviderConfig(name="MockProvider", enabled=True)
        provider = MockProvider(config)
        
        def check_data_types():
            results = []
            for data_type in [DataType.PRICE, DataType.HISTORICAL, DataType.FUNDAMENTALS]:
                results.append(provider.supports_data_type(data_type))
            return results
        
        results = benchmark(check_data_types)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_concurrent_provider_requests(self, benchmark, benchmark_asset):
        """Benchmark concurrent provider requests"""
        config = ProviderConfig(name="MockProvider", enabled=True)
        provider = MockProvider(config)
        
        import asyncio
        
        async def concurrent_requests():
            tasks = [provider.get_price(benchmark_asset) for _ in range(10)]
            return await asyncio.gather(*tasks)
        
        results = await benchmark.pedantic(concurrent_requests, rounds=5)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_provider_response_validation(self, benchmark, benchmark_asset):
        """Benchmark provider response validation"""
        config = ProviderConfig(name="MockProvider", enabled=True)
        provider = MockProvider(config)
        
        async def get_and_validate():
            response = await provider.get_price(benchmark_asset)
            # Validate response structure
            assert response.provider == "MockProvider"
            assert response.asset == benchmark_asset
            assert response.is_valid
            return response
        
        result = await benchmark.pedantic(get_and_validate, rounds=10)
        assert result is not None
