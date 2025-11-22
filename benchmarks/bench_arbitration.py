"""
Performance benchmarks for Data Arbitration Engine
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from fiml.arbitration.engine import DataArbitrationEngine
from fiml.core.models import DataType, ProviderHealth, ProviderScore
from fiml.providers.base import ProviderResponse


@pytest.fixture
def mock_providers():
    """Create mock providers for benchmarking"""
    providers = []
    for i in range(5):
        provider = AsyncMock()
        provider.name = f"Provider{i+1}"
        provider.config.enabled = True
        provider.get_health.return_value = ProviderHealth(
            provider_name=f"Provider{i+1}",
            is_available=True,
            uptime_percentage=95.0 + i,
            avg_latency_ms=100.0 + (i * 50),
            last_check=datetime.now(),
        )
        providers.append(provider)
    return providers


class TestArbitrationBenchmarks:
    """Benchmarks for arbitration engine"""

    def test_score_single_provider(self, benchmark, benchmark_asset, mock_providers):
        """Benchmark scoring a single provider"""
        engine = DataArbitrationEngine()
        
        def score_provider():
            return engine._score_provider(
                provider=mock_providers[0],
                asset=benchmark_asset,
                data_type=DataType.PRICE,
            )
        
        result = benchmark(score_provider)
        assert isinstance(result, ProviderScore)

    def test_score_multiple_providers(self, benchmark, benchmark_asset, mock_providers):
        """Benchmark scoring multiple providers"""
        engine = DataArbitrationEngine()
        
        def score_providers():
            scores = []
            for provider in mock_providers:
                score = engine._score_provider(
                    provider=provider,
                    asset=benchmark_asset,
                    data_type=DataType.PRICE,
                )
                scores.append(score)
            return scores
        
        results = benchmark(score_providers)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_create_arbitration_plan(self, benchmark, benchmark_asset, mock_providers):
        """Benchmark creating arbitration plan"""
        engine = DataArbitrationEngine()
        engine.provider_registry._providers = {p.name: p for p in mock_providers}
        
        async def create_plan():
            return await engine._create_arbitration_plan(
                asset=benchmark_asset,
                data_type=DataType.PRICE,
                user_region="US",
            )
        
        result = await benchmark.pedantic(create_plan, rounds=10)
        assert result is not None

    def test_conflict_resolution(self, benchmark, benchmark_asset):
        """Benchmark conflict resolution for multiple provider responses"""
        engine = DataArbitrationEngine()
        
        # Create mock responses with slight price differences
        responses = []
        for i in range(5):
            response = ProviderResponse(
                provider=f"Provider{i+1}",
                asset=benchmark_asset,
                data_type=DataType.PRICE,
                data={"price": 150.0 + i * 0.5, "volume": 1000000},
                timestamp=datetime.now(),
                confidence=0.95 - (i * 0.05),
            )
            responses.append(response)
        
        def resolve_conflicts():
            return engine._resolve_conflicts(responses)
        
        result = benchmark(resolve_conflicts)
        assert "price" in result
