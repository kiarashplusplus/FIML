"""
Tests for CoinGecko Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.coingecko import CoinGeckoProvider


@pytest.fixture
def crypto_asset():
    """Create a crypto asset for testing"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
    )


@pytest.mark.asyncio
async def test_coingecko_initialization():
    """Test CoinGecko provider initialization"""
    provider = CoinGeckoProvider()
    assert provider.name == "coingecko"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False


@pytest.mark.asyncio
async def test_coingecko_get_coin_id():
    """Test symbol to coin ID conversion"""
    provider = CoinGeckoProvider()
    
    # Direct mapping
    assert provider._get_coin_id("BTC") == "bitcoin"
    assert provider._get_coin_id("ETH") == "ethereum"
    
    # Suffix removal
    assert provider._get_coin_id("BTCUSDT") == "bitcoin"
    assert provider._get_coin_id("ETHBUSD") == "ethereum"
    
    # Lowercase fallback
    assert provider._get_coin_id("UNKNOWN") == "unknown"


@pytest.mark.asyncio
async def test_coingecko_fetch_price(crypto_asset):
    """Test fetching price from CoinGecko"""
    provider = CoinGeckoProvider()
    await provider.initialize()

    # Mock response
    mock_response = {
        "bitcoin": {
            "usd": 50000.0,
            "usd_market_cap": 1000000000000.0,
            "usd_24h_vol": 50000000000.0,
            "usd_24h_change": 2.5
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(crypto_asset)

        assert response.provider == "coingecko"
        assert response.asset == crypto_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 50000.0
        assert response.data["market_cap"] == 1000000000000.0
        assert response.data["change_24h"] == 2.5
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/simple/price"
        assert call_args[1]["ids"] == "bitcoin"


@pytest.mark.asyncio
async def test_coingecko_fetch_ohlcv(crypto_asset):
    """Test fetching OHLCV from CoinGecko"""
    provider = CoinGeckoProvider()
    await provider.initialize()

    # Mock response (timestamp, open, high, low, close)
    mock_response = [
        [1609459200000, 29000.0, 29500.0, 28500.0, 29300.0],
        [1609545600000, 29300.0, 30000.0, 29000.0, 29800.0]
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_ohlcv(crypto_asset, timeframe="1d")

        assert response.provider == "coingecko"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["ohlcv"]) == 2
        assert response.data["ohlcv"][0]["close"] == 29300.0
        assert response.data["ohlcv"][1]["close"] == 29800.0

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/coins/bitcoin/ohlc"


@pytest.mark.asyncio
async def test_coingecko_fetch_fundamentals(crypto_asset):
    """Test fetching fundamentals from CoinGecko"""
    provider = CoinGeckoProvider()
    await provider.initialize()

    # Mock response
    mock_response = {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "description": {"en": "Digital gold"},
        "market_cap_rank": 1,
        "market_data": {
            "market_cap": {"usd": 1000000000000},
            "total_volume": {"usd": 50000000000},
            "current_price": {"usd": 50000},
            "circulating_supply": 19000000,
            "total_supply": 21000000,
            "max_supply": 21000000
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_fundamentals(crypto_asset)

        assert response.provider == "coingecko"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["symbol"] == "BTC"
        assert response.data["name"] == "Bitcoin"
        assert response.data["market_cap"] == 1000000000000

        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "/coins/bitcoin"


@pytest.mark.asyncio
async def test_coingecko_supports_asset(crypto_asset):
    """Test asset support check"""
    provider = CoinGeckoProvider()
    
    assert await provider.supports_asset(crypto_asset) is True
    
    equity_asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
    assert await provider.supports_asset(equity_asset) is False


@pytest.mark.asyncio
async def test_coingecko_error_handling(crypto_asset):
    """Test error handling in CoinGecko provider"""
    provider = CoinGeckoProvider()
    await provider.initialize()

    # Test API Error
    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ProviderError("API Error")

        with pytest.raises(ProviderError):
            await provider.fetch_price(crypto_asset)

    # Test Rate Limit
    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ProviderRateLimitError("Rate limit exceeded")

        with pytest.raises(ProviderRateLimitError):
            await provider.fetch_price(crypto_asset)
