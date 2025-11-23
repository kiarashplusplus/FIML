"""
Additional tests for Data Arbitration Engine
"""

import pytest

from fiml.arbitration.engine import DataArbitrationEngine
from fiml.core.models import DataType
from fiml.providers.registry import provider_registry


class TestArbitrationEngineAdditional:
    """Additional tests for arbitration engine"""

    @pytest.mark.asyncio
    async def test_arbitrate_with_max_staleness(self, mock_asset):
        """Test arbitration with staleness constraint"""
        await provider_registry.initialize()

        engine = DataArbitrationEngine()

        plan = await engine.arbitrate_request(
            asset=mock_asset,
            data_type=DataType.PRICE,
            max_staleness_seconds=60  # 1 minute
        )

        assert plan is not None
        assert plan.primary_provider is not None

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_arbitrate_different_data_types(self, mock_asset):
        """Test arbitration for different data types"""
        await provider_registry.initialize()

        engine = DataArbitrationEngine()

        # Test various data types
        for data_type in [DataType.PRICE, DataType.OHLCV]:
            plan = await engine.arbitrate_request(
                asset=mock_asset,
                data_type=data_type,
            )
            assert plan is not None
            assert plan.primary_provider is not None

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_execute_with_primary_failure(self, mock_asset):
        """Test execution when primary provider fails"""
        await provider_registry.initialize()

        engine = DataArbitrationEngine()

        # Create a plan with fallback
        plan = await engine.arbitrate_request(
            asset=mock_asset,
            data_type=DataType.PRICE,
        )

        # The execute_with_fallback should handle failures gracefully
        response = await engine.execute_with_fallback(
            plan=plan,
            asset=mock_asset,
            data_type=DataType.PRICE,
        )

        assert response is not None

        await provider_registry.shutdown()
