"""
Tests for Marketstack Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.marketstack import MarketstackProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
    )


@pytest.mark.asyncio
async def test_marketstack_initialization():
    """Test Marketstack provider initialization"""
    # Test with API key
    provider = MarketstackProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch.object(settings, "marketstack_api_key", None):
        provider = MarketstackProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_marketstack_fetch_price(equity_asset):
    """Test fetching price from Marketstack"""
    provider = MarketstackProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "data": [
            {
                "open": 149.0,
                "high": 151.0,
                "low": 149.0,
                "close": 150.0,
                "volume": 1000000.0,
                "adj_high": 151.0,
                "adj_low": 149.0,
                "adj_close": 150.0,
                "adj_open": 149.0,
                "adj_volume": 1000000.0,
                "split_factor": 1.0,
                "dividend": 0.0,
                "symbol": "AAPL",
                "exchange": "XNAS",
                "date": "2021-01-01T00:00:00+0000"
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "marketstack"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["open"] == 149.0
        assert response.data["high"] == 151.0
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/eod/latest"
        assert call_args[1]["symbols"] == "AAPL"


@pytest.mark.asyncio
async def test_marketstack_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Marketstack"""
    provider = MarketstackProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "data": [
            {
                "open": 153.0,
                "high": 156.0,
                "low": 152.0,
                "close": 154.0,
                "volume": 1100000.0,
                "date": "2021-01-02T00:00:00+0000"
            },
            {
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 153.0,
                "volume": 1000000.0,
                "date": "2021-01-01T00:00:00+0000"
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "marketstack"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 154.0
        assert response.data["ohlcv"][1]["close"] == 153.0

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/eod"
        assert call_args[1]["symbols"] == "AAPL"


@pytest.mark.asyncio
async def test_marketstack_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Marketstack (limited)"""
    provider = MarketstackProvider(api_key="test_key")
    await provider.initialize()

    response = await provider.fetch_fundamentals(equity_asset)

    assert response.provider == "marketstack"
    assert response.data_type == DataType.FUNDAMENTALS
    assert response.data["symbol"] == "AAPL"
    assert response.data["note"] == "Limited fundamentals available"
    assert response.confidence == 0.5


@pytest.mark.asyncio
async def test_marketstack_fetch_news(equity_asset):
    """Test fetching news from Marketstack (unsupported)"""
    provider = MarketstackProvider(api_key="test_key")
    await provider.initialize()

    response = await provider.fetch_news(equity_asset)

    assert response.provider == "marketstack"
    assert response.data_type == DataType.NEWS
    assert response.is_valid is True
    assert len(response.data["articles"]) == 0


@pytest.mark.asyncio
async def test_marketstack_supports_asset(equity_asset):
    """Test asset support check"""
    provider = MarketstackProvider(api_key="test_key")
    
    assert await provider.supports_asset(equity_asset) is True
    
    index_asset = Asset(symbol="SPX", asset_type=AssetType.INDEX)
    assert await provider.supports_asset(index_asset) is True
    
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is False


@pytest.mark.asyncio
async def test_marketstack_error_handling(equity_asset):
    """Test error handling in Marketstack provider"""
    provider = MarketstackProvider(api_key="test_key")
    await provider.initialize()

    # Test API Error
    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ProviderError("API Error")

        with pytest.raises(ProviderError):
            await provider.fetch_price(equity_asset)

    # Test Rate Limit
    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ProviderRateLimitError("Rate limit exceeded")

        with pytest.raises(ProviderRateLimitError):
            await provider.fetch_price(equity_asset)
