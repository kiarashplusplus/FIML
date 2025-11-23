"""
Tests for Providers
"""

import pytest

from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.mock_provider import MockProvider
from fiml.providers.yahoo_finance import YahooFinanceProvider


@pytest.mark.asyncio
async def test_mock_provider_fetch_price(mock_asset):
    """Test mock provider price fetch"""
    provider = MockProvider()
    await provider.initialize()

    response = await provider.fetch_price(mock_asset)

    assert response is not None
    assert response.provider == "mock_provider"
    assert response.data_type == DataType.PRICE
    assert "price" in response.data
    assert response.is_valid

    await provider.shutdown()


@pytest.mark.asyncio
async def test_yahoo_finance_provider_supports_equity():
    """Test Yahoo Finance provider supports equity"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    asset = Asset(
        symbol="AAPL",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )

    supports = await provider.supports_asset(asset)
    assert supports is True

    await provider.shutdown()


@pytest.mark.asyncio
async def test_yahoo_finance_provider_health():
    """Test Yahoo Finance provider health"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    health = await provider.get_health()

    assert health is not None
    assert health.provider_name == "yahoo_finance"
    assert health.is_healthy is True

    await provider.shutdown()
