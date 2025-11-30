"""
Tests for Twelvedata Provider
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.twelvedata import TwelvedataProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
    )


@pytest.mark.asyncio
async def test_twelvedata_initialization():
    """Test Twelvedata provider initialization"""
    # Test with API key
    provider = TwelvedataProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch.object(settings, "twelvedata_api_key", None):
        provider = TwelvedataProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_twelvedata_fetch_price(equity_asset):
    """Test fetching price from Twelvedata"""
    provider = TwelvedataProvider(api_key="test_key")
    await provider.initialize()

    # Mock responses
    mock_price_response = {"price": 150.0}
    mock_quote_response = {
        "open": 149.0,
        "high": 151.0,
        "low": 149.0,
        "close": 150.0,
        "volume": 1000000,
        "change": 1.0,
        "percent_change": 0.67,
        "previous_close": 149.0
    }

    # Mock the session.get method
    # session.get returns a context manager, not a coroutine
    mock_get = MagicMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.status = 200
    mock_context.__aenter__.return_value.json.side_effect = [mock_price_response, mock_quote_response]
    mock_get.return_value = mock_context
    
    with patch.object(provider._session, "get", mock_get):
        response = await provider.fetch_price(equity_asset)

        assert response.provider == "twelvedata"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["open"] == 149.0
        assert response.is_valid is True


@pytest.mark.asyncio
async def test_twelvedata_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Twelvedata"""
    provider = TwelvedataProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "values": [
            {
                "datetime": "2021-01-01 00:00:00",
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 153.0,
                "volume": 1000000
            },
            {
                "datetime": "2021-01-02 00:00:00",
                "open": 153.0,
                "high": 156.0,
                "low": 152.0,
                "close": 154.0,
                "volume": 1100000
            }
        ]
    }

    mock_get = MagicMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.status = 200
    mock_context.__aenter__.return_value.json.return_value = mock_response
    mock_get.return_value = mock_context

    with patch.object(provider._session, "get", mock_get):
        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "twelvedata"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 153.0


@pytest.mark.asyncio
async def test_twelvedata_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Twelvedata"""
    provider = TwelvedataProvider(api_key="test_key")
    await provider.initialize()

    # Mock responses
    mock_profile_response = {
        "symbol": "AAPL",
        "name": "Apple Inc",
        "exchange": "NASDAQ",
        "currency": "USD",
        "country": "United States",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "employees": 100000
    }
    mock_stats_response = {
        "statistics": {
            "valuations_metrics": {
                "market_capitalization": 2000000000000,
                "pe_ratio": 25.0,
                "peg_ratio": 1.5,
                "book_value": 5.0,
                "dividend_yield": 0.005,
                "earnings_per_share": 6.0
            }
        }
    }

    mock_get = MagicMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.status = 200
    mock_context.__aenter__.return_value.json.side_effect = [mock_profile_response, mock_stats_response]
    mock_get.return_value = mock_context

    with patch.object(provider._session, "get", mock_get):
        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "twelvedata"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["symbol"] == "AAPL"
        assert response.data["market_cap"] == 2000000000000


@pytest.mark.asyncio
async def test_twelvedata_fetch_news(equity_asset):
    """Test fetching news from Twelvedata (unsupported)"""
    provider = TwelvedataProvider(api_key="test_key")
    await provider.initialize()

    response = await provider.fetch_news(equity_asset)

    assert response.provider == "twelvedata"
    assert response.data_type == DataType.NEWS
    assert response.is_valid is True
    assert len(response.data["articles"]) == 0


@pytest.mark.asyncio
async def test_twelvedata_supports_asset(equity_asset):
    """Test asset support check"""
    provider = TwelvedataProvider(api_key="test_key")
    
    assert await provider.supports_asset(equity_asset) is True
    
    crypto_asset = Asset(symbol="BTC/USD", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is True
    
    forex_asset = Asset(symbol="EUR/USD", asset_type=AssetType.FOREX)
    assert await provider.supports_asset(forex_asset) is True


@pytest.mark.asyncio
async def test_twelvedata_error_handling(equity_asset):
    """Test error handling in Twelvedata provider"""
    provider = TwelvedataProvider(api_key="test_key")
    await provider.initialize()

    # Test API Error (non-200 status)
    mock_get_error = MagicMock()
    mock_context_error = AsyncMock()
    mock_context_error.__aenter__.return_value.status = 500
    mock_context_error.__aenter__.return_value.text.return_value = "Internal Server Error"
    mock_get_error.return_value = mock_context_error

    with patch.object(provider._session, "get", mock_get_error):
        with pytest.raises(ProviderError):
            await provider.fetch_price(equity_asset)

    # Test Rate Limit (429 status)
    mock_get_rate = MagicMock()
    mock_context_rate = AsyncMock()
    mock_context_rate.__aenter__.return_value.status = 429
    mock_get_rate.return_value = mock_context_rate

    with patch.object(provider._session, "get", mock_get_rate):
        with pytest.raises(ProviderRateLimitError):
            await provider.fetch_price(equity_asset)

    # Test API Error (200 status but error in body)
    mock_get_api_error = AsyncMock()
    mock_get_api_error.__aenter__.return_value.status = 200
    mock_get_api_error.__aenter__.return_value.json.return_value = {
        "status": "error",
        "message": "Invalid API key"
    }

    with patch.object(provider._session, "get", mock_get_api_error):
        with pytest.raises(ProviderError):
            await provider.fetch_price(equity_asset)
