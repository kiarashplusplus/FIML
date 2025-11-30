"""
Tests for Intrinio Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.intrinio import IntrinioProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
    )


@pytest.mark.asyncio
async def test_intrinio_initialization():
    """Test Intrinio provider initialization"""
    # Test with API key
    provider = IntrinioProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch.object(settings, "intrinio_api_key", None):
        provider = IntrinioProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_intrinio_fetch_price(equity_asset):
    """Test fetching price from Intrinio"""
    provider = IntrinioProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "last_price": 150.0,
        "bid_price": 149.9,
        "bid_size": 100,
        "ask_price": 150.1,
        "ask_size": 200,
        "open_price": 149.0,
        "high_price": 151.0,
        "low_price": 149.0,
        "volume": 1000000,
        "last_time": "2021-01-01T12:00:00Z",
        "source": "iex"
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "intrinio"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["bid_price"] == 149.9
        assert response.data["ask_price"] == 150.1
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/securities/AAPL/prices/realtime"


@pytest.mark.asyncio
async def test_intrinio_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Intrinio"""
    provider = IntrinioProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "stock_prices": [
            {
                "date": "2021-01-01",
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 153.0,
                "volume": 1000000,
                "adj_close": 153.0
            },
            {
                "date": "2021-01-02",
                "open": 153.0,
                "high": 156.0,
                "low": 152.0,
                "close": 154.0,
                "volume": 1100000,
                "adj_close": 154.0
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "intrinio"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 153.0
        assert response.data["ohlcv"][1]["close"] == 154.0

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/securities/AAPL/prices"


@pytest.mark.asyncio
async def test_intrinio_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Intrinio"""
    provider = IntrinioProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "ticker": "AAPL",
        "name": "Apple Inc",
        "lei": "123456",
        "cik": "0000320193",
        "stock_exchange": "NASDAQ",
        "sector": "Technology",
        "hq_country": "USA"
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "intrinio"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["symbol"] == "AAPL"
        assert response.data["cik"] == "0000320193"
        assert response.data["sector"] == "Technology"

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/companies/AAPL"


@pytest.mark.asyncio
async def test_intrinio_fetch_news(equity_asset):
    """Test fetching news from Intrinio"""
    provider = IntrinioProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "news": [
            {
                "title": "Apple launches new iPhone",
                "url": "https://example.com/news",
                "summary": "New iPhone details...",
                "publication_date": "2021-01-01T12:00:00Z",
                "company": {"name": "Apple Inc"}
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_news(equity_asset)

        assert response.provider == "intrinio"
        assert response.data_type == DataType.NEWS
        assert len(response.data["articles"]) == 1
        assert response.data["articles"][0]["title"] == "Apple launches new iPhone"

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/companies/AAPL/news"


@pytest.mark.asyncio
async def test_intrinio_supports_asset(equity_asset):
    """Test asset support check"""
    provider = IntrinioProvider(api_key="test_key")
    
    assert await provider.supports_asset(equity_asset) is True
    
    option_asset = Asset(symbol="AAPL210101C150", asset_type=AssetType.OPTION)
    assert await provider.supports_asset(option_asset) is True
    
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is False


@pytest.mark.asyncio
async def test_intrinio_error_handling(equity_asset):
    """Test error handling in Intrinio provider"""
    provider = IntrinioProvider(api_key="test_key")
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
