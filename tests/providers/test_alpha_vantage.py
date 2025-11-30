"""
Tests for Alpha Vantage Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.alpha_vantage import AlphaVantageProvider


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="IBM",
        name="IBM",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )


@pytest.fixture
def forex_asset():
    """Create a forex asset for testing"""
    return Asset(
        symbol="EURUSD",
        name="Euro / US Dollar",
        asset_type=AssetType.FOREX,
    )


@pytest.mark.asyncio
async def test_alpha_vantage_initialization():
    """Test Alpha Vantage provider initialization"""
    # Test with API key
    provider = AlphaVantageProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch.object(settings, "alpha_vantage_api_key", None):
        provider = AlphaVantageProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_alpha_vantage_fetch_price(equity_asset):
    """Test fetching price from Alpha Vantage"""
    provider = AlphaVantageProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "Global Quote": {
            "01. symbol": "IBM",
            "05. price": "150.00",
            "09. change": "2.00",
            "10. change percent": "1.5%",
            "06. volume": "1000000",
            "08. previous close": "148.00",
            "02. open": "149.00",
            "03. high": "151.00",
            "04. low": "149.00",
            "07. latest trading day": "2023-01-01"
        }
    }

    # Mock _make_request
    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "alpha_vantage"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["change"] == 2.0
        assert response.data["change_percent"] == 1.5
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0][0]
        assert call_args["function"] == "GLOBAL_QUOTE"
        assert call_args["symbol"] == "IBM"


@pytest.mark.asyncio
async def test_alpha_vantage_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Alpha Vantage"""
    provider = AlphaVantageProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "Meta Data": {
            "1. Information": "Daily Prices (open, high, low, close) and Volumes",
            "2. Symbol": "IBM",
            "3. Last Refreshed": "2023-01-02",
            "4. Output Size": "Compact",
            "5. Time Zone": "US/Eastern"
        },
        "Time Series (Daily)": {
            "2023-01-02": {
                "1. open": "150.00",
                "2. high": "155.00",
                "3. low": "149.00",
                "4. close": "153.00",
                "5. volume": "1200000"
            },
            "2023-01-01": {
                "1. open": "148.00",
                "2. high": "152.00",
                "3. low": "147.00",
                "4. close": "150.00",
                "5. volume": "1000000"
            }
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "alpha_vantage"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 153.0
        assert response.data["ohlcv"][1]["close"] == 150.0

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0][0]
        assert call_args["function"] == "TIME_SERIES_DAILY"


@pytest.mark.asyncio
async def test_alpha_vantage_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Alpha Vantage"""
    provider = AlphaVantageProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "Symbol": "IBM",
        "Name": "International Business Machines",
        "MarketCapitalization": "120000000000",
        "PERatio": "20.5",
        "Sector": "Technology",
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "alpha_vantage"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["market_cap"] == 120000000000
        assert response.data["pe_ratio"] == 20.5
        assert response.data["sector"] == "Technology"

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0][0]
        assert call_args["function"] == "OVERVIEW"


@pytest.mark.asyncio
async def test_alpha_vantage_supports_asset(equity_asset, forex_asset):
    """Test asset support check"""
    provider = AlphaVantageProvider(api_key="test_key")
    await provider.initialize()

    assert await provider.supports_asset(equity_asset) is True
    assert await provider.supports_asset(forex_asset) is True

    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO)
    assert await provider.supports_asset(crypto_asset) is False


@pytest.mark.asyncio
async def test_alpha_vantage_error_handling(equity_asset):
    """Test error handling in Alpha Vantage provider"""
    provider = AlphaVantageProvider(api_key="test_key")
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
