"""
Tests for Financial Modeling Prep (FMP) Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.fmp import FMPProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
    )


@pytest.mark.asyncio
async def test_fmp_initialization():
    """Test FMP provider initialization"""
    # Test with API key
    provider = FMPProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should log warning and not initialize)
    with patch.object(settings, "fmp_api_key", None):
        provider = FMPProvider(api_key=None)
        await provider.initialize()
        assert provider._is_initialized is False


@pytest.mark.asyncio
async def test_fmp_fetch_price(equity_asset):
    """Test fetching price from FMP"""
    provider = FMPProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = [
        {
            "symbol": "AAPL",
            "price": 150.0,
            "change": 2.0,
            "changesPercentage": 1.5,
            "volume": 1000000,
            "previousClose": 148.0,
            "open": 149.0,
            "dayHigh": 151.0,
            "dayLow": 149.0,
            "marketCap": 2000000000000,
            "pe": 25.0,
            "eps": 6.0,
            "sharesOutstanding": 16000000000,
            "timestamp": 1609459200
        }
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "fmp"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["change"] == 2.0
        assert response.data["change_percent"] == 1.5
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "quote"
        assert call_args[1]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_fmp_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from FMP"""
    provider = FMPProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "symbol": "AAPL",
        "historical": [
            {
                "date": "2021-01-01",
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 153.0,
                "volume": 1000000
            },
            {
                "date": "2021-01-02",
                "open": 153.0,
                "high": 156.0,
                "low": 152.0,
                "close": 154.0,
                "volume": 1100000
            }
        ]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "fmp"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 153.0
        assert response.data["ohlcv"][1]["close"] == 154.0

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "historical-price-eod/full"
        assert call_args[1]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_fmp_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from FMP"""
    provider = FMPProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = [
        {
            "symbol": "AAPL",
            "companyName": "Apple Inc",
            "description": "Tech giant",
            "exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "website": "https://apple.com",
            "ceo": "Tim Cook",
            "fullTimeEmployees": "100000",
            "mktCap": 2000000000000,
            "price": 150.0,
            "beta": 1.2,
            "volAvg": 1000000,
            "lastDiv": 0.8,
            "changes": 2.0
        }
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "fmp"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["symbol"] == "AAPL"
        assert response.data["market_cap"] == 2000000000000
        assert response.data["sector"] == "Technology"

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "profile"
        assert call_args[1]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_fmp_fetch_news(equity_asset):
    """Test fetching news from FMP (unsupported)"""
    provider = FMPProvider(api_key="test_key")
    await provider.initialize()

    response = await provider.fetch_news(equity_asset)

    assert response.provider == "fmp"
    assert response.data_type == DataType.NEWS
    assert response.is_valid is False
    assert len(response.data["articles"]) == 0


@pytest.mark.asyncio
async def test_fmp_supports_asset(equity_asset):
    """Test asset support check"""
    provider = FMPProvider(api_key="test_key")
    
    assert await provider.supports_asset(equity_asset) is True
    
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is False


@pytest.mark.asyncio
async def test_fmp_error_handling(equity_asset):
    """Test error handling in FMP provider"""
    provider = FMPProvider(api_key="test_key")
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
