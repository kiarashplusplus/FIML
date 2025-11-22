"""
Tests for Data Arbitration Engine
"""

import pytest
from fiml.arbitration.engine import DataArbitrationEngine
from fiml.core.models import Asset, AssetType, DataType, Market


@pytest.mark.asyncio
async def test_arbitrate_request(mock_asset):
    """Test basic arbitration request"""
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


@pytest.mark.asyncio
async def test_execute_with_fallback(mock_asset):
    """Test execution with fallback"""
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
