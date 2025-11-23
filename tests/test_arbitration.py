"""
Tests for Data Arbitration Engine
"""

import pytest

from fiml.arbitration.engine import DataArbitrationEngine
from fiml.core.models import DataType
from fiml.providers.registry import provider_registry


@pytest.mark.asyncio
async def test_arbitrate_request(mock_asset):
    """Test basic arbitration request"""
    # Initialize provider registry
    await provider_registry.initialize()

    engine = DataArbitrationEngine()

    plan = await engine.arbitrate_request(
        asset=mock_asset,
        data_type=DataType.PRICE,
        user_region="US",
        max_staleness_seconds=300,
    )

    assert plan.primary_provider is not None
    assert isinstance(plan.fallback_providers, list)
    assert plan.estimated_latency_ms > 0

    await provider_registry.shutdown()


@pytest.mark.asyncio
async def test_execute_with_fallback(mock_asset):
    """Test execution with fallback"""
    # Initialize provider registry
    await provider_registry.initialize()

    engine = DataArbitrationEngine()

    # First create a plan
    plan = await engine.arbitrate_request(
        asset=mock_asset,
        data_type=DataType.PRICE,
    )

    # Then execute it
    response = await engine.execute_with_fallback(
        plan=plan,
        asset=mock_asset,
        data_type=DataType.PRICE,
    )

    assert response is not None
    assert response.is_valid
    assert response.data is not None
    assert "price" in response.data

    await provider_registry.shutdown()
