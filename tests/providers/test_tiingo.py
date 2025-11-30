"""
Tests for Tiingo Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.tiingo import TiingoProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
    )


@pytest.mark.asyncio
async def test_tiingo_initialization():
    """Test Tiingo provider initialization"""
    # Test with API key
    provider = TiingoProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch.object(settings, "tiingo_api_key", None):
        provider = TiingoProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_tiingo_fetch_price(equity_asset):
    """Test fetching price from Tiingo"""
    provider = TiingoProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = [
        {
            "close": 150.0,
            "open": 149.0,
            "high": 151.0,
            "low": 149.0,
            "volume": 1000000,
            "adjClose": 150.0,
            "divCash": 0.0,
            "splitFactor": 1.0,
            "date": "2021-01-01T00:00:00Z"
        }
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "tiingo"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["open"] == 149.0
        assert response.data["high"] == 151.0
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/tiingo/daily/AAPL/prices"


@pytest.mark.asyncio
async def test_tiingo_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Tiingo"""
    provider = TiingoProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = [
        {
            "date": "2021-01-01T00:00:00Z",
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 153.0,
            "volume": 1000000,
            "adjClose": 153.0,
            "adjHigh": 155.0,
            "adjLow": 149.0,
            "adjOpen": 150.0,
            "adjVolume": 1000000
        },
        {
            "date": "2021-01-02T00:00:00Z",
            "open": 153.0,
            "high": 156.0,
            "low": 152.0,
            "close": 154.0,
            "volume": 1100000,
            "adjClose": 154.0,
            "adjHigh": 156.0,
            "adjLow": 152.0,
            "adjOpen": 153.0,
            "adjVolume": 1100000
        }
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "tiingo"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 153.0
        assert response.data["ohlcv"][1]["close"] == 154.0

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/tiingo/daily/AAPL/prices"


@pytest.mark.asyncio
async def test_tiingo_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Tiingo"""
    provider = TiingoProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "ticker": "AAPL",
        "name": "Apple Inc",
        "exchangeCode": "NASDAQ",
        "description": "Tech giant",
        "startDate": "1980-12-12",
        "endDate": "2021-01-01"
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "tiingo"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["symbol"] == "AAPL"
        assert response.data["exchange_code"] == "NASDAQ"

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/tiingo/daily/AAPL"


@pytest.mark.asyncio
async def test_tiingo_fetch_news(equity_asset):
    """Test fetching news from Tiingo"""
    provider = TiingoProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = [
        {
            "title": "Apple launches new iPhone",
            "url": "https://example.com/news",
            "source": "TechNews",
            "publishedDate": "2021-01-01T12:00:00Z",
            "description": "New iPhone details...",
            "tags": ["Technology", "Mobile"]
        }
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_news(equity_asset)

        assert response.provider == "tiingo"
        assert response.data_type == DataType.NEWS
        assert len(response.data["articles"]) == 1
        assert response.data["articles"][0]["title"] == "Apple launches new iPhone"

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/tiingo/news"


@pytest.mark.asyncio
async def test_tiingo_supports_asset(equity_asset):
    """Test asset support check"""
    provider = TiingoProvider(api_key="test_key")
    
    assert await provider.supports_asset(equity_asset) is True
    
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is True
    
    forex_asset = Asset(symbol="EURUSD", asset_type=AssetType.FOREX)
    assert await provider.supports_asset(forex_asset) is False


@pytest.mark.asyncio
async def test_tiingo_error_handling(equity_asset):
    """Test error handling in Tiingo provider"""
    provider = TiingoProvider(api_key="test_key")
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
