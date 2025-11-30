"""
Tests for Finnhub Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.finnhub import FinnhubProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
    )


from fiml.core.config import settings

# ... imports ...

@pytest.mark.asyncio
async def test_finnhub_initialization():
    """Test Finnhub provider initialization"""
    # Test with API key
    provider = FinnhubProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch.object(settings, "finnhub_api_key", None):
        provider = FinnhubProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_finnhub_fetch_price(equity_asset):
    """Test fetching price from Finnhub"""
    provider = FinnhubProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "c": 150.0,
        "d": 2.0,
        "dp": 1.5,
        "h": 151.0,
        "l": 149.0,
        "o": 149.0,
        "pc": 148.0,
        "t": 1609459200
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "finnhub"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["change"] == 2.0
        assert response.data["change_percent"] == 1.5
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/quote"
        assert call_args[1]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_finnhub_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Finnhub"""
    provider = FinnhubProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "s": "ok",
        "t": [1609459200, 1609545600],
        "o": [150.0, 151.0],
        "h": [155.0, 156.0],
        "l": [149.0, 150.0],
        "c": [153.0, 154.0],
        "v": [1000000, 1100000]
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "finnhub"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 153.0
        assert response.data["ohlcv"][1]["close"] == 154.0

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/stock/candle"
        assert call_args[1]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_finnhub_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Finnhub"""
    provider = FinnhubProvider(api_key="test_key")
    await provider.initialize()

    # Mock responses
    mock_profile = {
        "ticker": "AAPL",
        "name": "Apple Inc",
        "marketCapitalization": 2000000,
        "shareOutstanding": 16000,
        "finnhubIndustry": "Technology"
    }
    
    mock_metrics = {
        "metric": {
            "52WeekHigh": 180.0,
            "52WeekLow": 120.0,
            "peBasicExclExtraTTM": 25.0
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [mock_profile, mock_metrics]

        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "finnhub"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["symbol"] == "AAPL"
        assert response.data["market_cap"] == 2000000000000.0  # 2M * 1M
        assert response.data["pe_ratio"] == 25.0
        assert response.data["industry"] == "Technology"

        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_finnhub_fetch_news(equity_asset):
    """Test fetching news from Finnhub"""
    provider = FinnhubProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = [
        {
            "headline": "Apple launches new iPhone",
            "url": "https://example.com/news",
            "source": "TechNews",
            "datetime": 1609459200,
            "summary": "New iPhone details..."
        }
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_news(equity_asset)

        assert response.provider == "finnhub"
        assert response.data_type == DataType.NEWS
        assert len(response.data["articles"]) == 1
        assert response.data["articles"][0]["title"] == "Apple launches new iPhone"

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/company-news"


@pytest.mark.asyncio
async def test_finnhub_supports_asset(equity_asset):
    """Test asset support check"""
    provider = FinnhubProvider(api_key="test_key")
    
    assert await provider.supports_asset(equity_asset) is True
    
    forex_asset = Asset(symbol="EURUSD", asset_type=AssetType.FOREX)
    assert await provider.supports_asset(forex_asset) is True
    
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is True
    
    commodity_asset = Asset(symbol="GOLD", asset_type=AssetType.COMMODITY)
    assert await provider.supports_asset(commodity_asset) is False


@pytest.mark.asyncio
async def test_finnhub_error_handling(equity_asset):
    """Test error handling in Finnhub provider"""
    provider = FinnhubProvider(api_key="test_key")
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
