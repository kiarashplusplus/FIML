"""
Tests for Polygon Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.polygon import PolygonProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )


@pytest.fixture
def crypto_asset():
    """Create a crypto asset for testing"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
    )


@pytest.mark.asyncio
async def test_polygon_initialization():
    """Test Polygon provider initialization"""
    # Test with API key
    provider = PolygonProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch("fiml.core.config.settings.polygon_api_key", None):
        provider = PolygonProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_polygon_fetch_price(equity_asset):
    """Test fetching price from Polygon"""
    provider = PolygonProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "status": "OK",
        "ticker": "AAPL",
        "results": [
            {
                "c": 150.0,
                "o": 149.0,
                "h": 151.0,
                "l": 148.0,
                "v": 1000000,
                "vw": 149.5,
                "t": 1672531200000
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "polygon"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["volume"] == 1000000
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "/v2/aggs/ticker/AAPL/prev"


@pytest.mark.asyncio
async def test_polygon_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Polygon"""
    provider = PolygonProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "status": "OK",
        "ticker": "AAPL",
        "results": [
            {
                "t": 1672531200000,
                "o": 149.0,
                "h": 151.0,
                "l": 148.0,
                "c": 150.0,
                "v": 1000000,
                "vw": 149.5
            },
            {
                "t": 1672617600000,
                "o": 150.0,
                "h": 153.0,
                "l": 149.0,
                "c": 152.0,
                "v": 1100000,
                "vw": 151.0
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "polygon"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 150.0
        assert response.data["ohlcv"][1]["close"] == 152.0

        mock_request.assert_called_once()
        # Check if endpoint contains correct path segments
        call_args = mock_request.call_args
        assert "/v2/aggs/ticker/AAPL/range/1/day/" in call_args[0][0]


@pytest.mark.asyncio
async def test_polygon_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Polygon"""
    provider = PolygonProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "status": "OK",
        "results": {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "market_cap": 2000000000000,
            "primary_exchange": "NASDAQ",
            "total_employees": 150000
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "polygon"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["name"] == "Apple Inc."
        assert response.data["market_cap"] == 2000000000000
        assert response.data["primary_exchange"] == "NASDAQ"

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "/v3/reference/tickers/AAPL"


@pytest.mark.asyncio
async def test_polygon_fetch_news(equity_asset):
    """Test fetching news from Polygon"""
    provider = PolygonProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "status": "OK",
        "results": [
            {
                "title": "Apple News",
                "article_url": "https://example.com/news",
                "publisher": {"name": "Tech News"},
                "published_utc": "2023-01-01T12:00:00Z",
                "description": "News description"
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_news(equity_asset)

        assert response.provider == "polygon"
        assert response.data_type == DataType.NEWS
        assert len(response.data["articles"]) == 1
        assert response.data["articles"][0]["title"] == "Apple News"
        assert response.data["articles"][0]["publisher"] == "Tech News"

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "/v2/reference/news"


@pytest.mark.asyncio
async def test_polygon_supports_asset(equity_asset, crypto_asset):
    """Test asset support check"""
    provider = PolygonProvider(api_key="test_key")
    await provider.initialize()

    assert await provider.supports_asset(equity_asset) is True
    assert await provider.supports_asset(crypto_asset) is True

    # Test unsupported asset type (e.g., COMMODITY if not supported)
    # Assuming Polygon supports EQUITY, CRYPTO, FOREX, OPTION
    commodity_asset = Asset(symbol="GOLD", asset_type=AssetType.COMMODITY)
    assert await provider.supports_asset(commodity_asset) is False


@pytest.mark.asyncio
async def test_polygon_error_handling(equity_asset):
    """Test error handling in Polygon provider"""
    provider = PolygonProvider(api_key="test_key")
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
