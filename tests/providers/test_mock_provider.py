"""
Tests for Mock Provider
"""

import pytest

from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.mock_provider import MockProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
    )


@pytest.mark.asyncio
async def test_mock_initialization():
    """Test Mock provider initialization"""
    provider = MockProvider()
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True

    await provider.shutdown()
    assert provider._is_initialized is False


@pytest.mark.asyncio
async def test_mock_fetch_price(equity_asset):
    """Test fetching price from Mock provider"""
    provider = MockProvider()
    await provider.initialize()

    response = await provider.fetch_price(equity_asset)

    assert response.provider == "mock_provider"
    assert response.asset == equity_asset
    assert response.data_type == DataType.PRICE
    assert response.data["price"] == 100.0
    assert response.is_valid is True
    assert response.confidence == 1.0


@pytest.mark.asyncio
async def test_mock_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Mock provider"""
    provider = MockProvider()
    await provider.initialize()

    response = await provider.fetch_ohlcv(equity_asset, timeframe="1d", limit=10)

    assert response.provider == "mock_provider"
    assert response.data_type == DataType.OHLCV
    assert len(response.data["candles"]) == 10
    assert response.data["timeframe"] == "1d"
    assert response.is_valid is True


@pytest.mark.asyncio
async def test_mock_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Mock provider"""
    provider = MockProvider()
    await provider.initialize()

    response = await provider.fetch_fundamentals(equity_asset)

    assert response.provider == "mock_provider"
    assert response.data_type == DataType.FUNDAMENTALS
    assert response.data["market_cap"] == 100000000000
    assert response.is_valid is True


@pytest.mark.asyncio
async def test_mock_fetch_technical(equity_asset):
    """Test fetching technicals from Mock provider"""
    provider = MockProvider()
    await provider.initialize()

    response = await provider.fetch_technical(equity_asset)

    assert response.provider == "mock_provider"
    assert response.data_type == DataType.TECHNICAL
    assert response.data["rsi"] == 65.5
    assert response.is_valid is True


@pytest.mark.asyncio
async def test_mock_fetch_news(equity_asset):
    """Test fetching news from Mock provider"""
    provider = MockProvider()
    await provider.initialize()

    response = await provider.fetch_news(equity_asset, limit=5)

    assert response.provider == "mock_provider"
    assert response.data_type == DataType.NEWS
    assert len(response.data["articles"]) == 5
    assert response.is_valid is True


@pytest.mark.asyncio
async def test_mock_supports_asset(equity_asset):
    """Test asset support check"""
    provider = MockProvider()
    
    assert await provider.supports_asset(equity_asset) is True
    
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is True


@pytest.mark.asyncio
async def test_mock_health():
    """Test health check"""
    provider = MockProvider()
    await provider.initialize()

    health = await provider.get_health()
    assert health.is_healthy is True
    assert health.uptime_percent == 1.0
