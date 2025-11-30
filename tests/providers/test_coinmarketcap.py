"""
Tests for CoinMarketCap Provider
"""

from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.exceptions import ProviderError, ProviderRateLimitError
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.coinmarketcap import CoinMarketCapProvider


@pytest.fixture
def crypto_asset():
    """Create a crypto asset for testing"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
    )
from fiml.core.config import settings


@pytest.fixture
def equity_asset():
    """Create an equity asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )


@pytest.mark.asyncio
async def test_coinmarketcap_initialization():
    """Test CoinMarketCap provider initialization"""
    # Test with API key
    provider = CoinMarketCapProvider(api_key="test_key")
    assert provider.config.api_key == "test_key"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True
    assert provider._session is not None

    await provider.shutdown()
    assert provider._session.closed
    assert provider._is_initialized is False

    # Test without API key (should raise error if not in settings)
    with patch.object(settings, "coinmarketcap_api_key", None):
        provider = CoinMarketCapProvider(api_key=None)
        with pytest.raises(ProviderError):
            await provider.initialize()


@pytest.mark.asyncio
async def test_coinmarketcap_fetch_price(crypto_asset):
    """Test fetching price from CoinMarketCap"""
    provider = CoinMarketCapProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "data": {
            "BTC": {
                "id": 1,
                "name": "Bitcoin",
                "symbol": "BTC",
                "quote": {
                    "USD": {
                        "price": 50000.0,
                        "volume_24h": 1000000.0,
                        "volume_change_24h": 5.0,
                        "percent_change_1h": 0.1,
                        "percent_change_24h": 2.0,
                        "percent_change_7d": 10.0,
                        "market_cap": 1000000000.0,
                        "market_cap_dominance": 40.0,
                        "fully_diluted_market_cap": 1100000000.0,
                        "last_updated": "2023-01-01T00:00:00.000Z"
                    }
                },
                "cmc_rank": 1,
                "num_market_pairs": 1000
            }
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_price(crypto_asset)

        assert response.provider == "coinmarketcap"
        assert response.asset == crypto_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 50000.0
        assert response.data["percent_change_24h"] == 2.0
        assert response.is_valid is True

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "/cryptocurrency/quotes/latest"
        assert call_args[0][1]["symbol"] == "BTC"


@pytest.mark.asyncio
async def test_coinmarketcap_fetch_fundamentals(crypto_asset):
    """Test fetching fundamentals from CoinMarketCap"""
    provider = CoinMarketCapProvider(api_key="test_key")
    await provider.initialize()

    # Mock response
    mock_response = {
        "data": {
            "BTC": {
                "id": 1,
                "name": "Bitcoin",
                "symbol": "BTC",
                "category": "coin",
                "description": "Bitcoin description",
                "slug": "bitcoin",
                "logo": "https://example.com/btc.png",
                "date_launched": "2010-01-01",
                "tags": ["mineable"],
                "platform": None,
                "urls": {"website": ["https://bitcoin.org"]}
            }
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        response = await provider.fetch_fundamentals(crypto_asset)

        assert response.provider == "coinmarketcap"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["name"] == "Bitcoin"
        assert response.data["description"] == "Bitcoin description"
        assert response.data["category"] == "coin"

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "/cryptocurrency/info"


@pytest.mark.asyncio
async def test_coinmarketcap_fetch_ohlcv(crypto_asset):
    """Test fetching OHLCV from CoinMarketCap (should raise error)"""
    provider = CoinMarketCapProvider(api_key="test_key")
    await provider.initialize()

    with pytest.raises(ProviderError, match="OHLCV data requires CoinMarketCap paid plan"):
        await provider.fetch_ohlcv(crypto_asset)


@pytest.mark.asyncio
async def test_coinmarketcap_fetch_news(crypto_asset):
    """Test fetching news from CoinMarketCap (returns empty)"""
    provider = CoinMarketCapProvider(api_key="test_key")
    await provider.initialize()

    response = await provider.fetch_news(crypto_asset)

    assert response.provider == "coinmarketcap"
    assert response.data_type == DataType.NEWS
    assert response.data["articles"] == []
    assert response.is_fresh is False


@pytest.mark.asyncio
async def test_coinmarketcap_supports_asset(crypto_asset, equity_asset):
    """Test asset support check"""
    provider = CoinMarketCapProvider(api_key="test_key")
    await provider.initialize()

    assert await provider.supports_asset(crypto_asset) is True
    assert await provider.supports_asset(equity_asset) is False


@pytest.mark.asyncio
async def test_coinmarketcap_error_handling(crypto_asset):
    """Test error handling in CoinMarketCap provider"""
    provider = CoinMarketCapProvider(api_key="test_key")
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
