"""
Tests for CCXT Provider
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from fiml.core.exceptions import ProviderError, ProviderTimeoutError, RegionalRestrictionError
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.base import ProviderResponse
from fiml.providers.ccxt_provider import CCXTMultiExchangeProvider, CCXTProvider


@pytest.fixture
def crypto_asset():
    """Create a crypto asset for testing"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
    )


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
async def test_ccxt_provider_initialization():
    """Test CCXT provider initialization"""
    provider = CCXTProvider(exchange_id="binance")

    assert provider.name == "ccxt_binance"
    assert provider.exchange_id == "binance"
    assert provider._is_initialized is False

    # Mock ccxt exchange
    with patch("fiml.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_exchange = AsyncMock()
        mock_exchange.load_markets = AsyncMock()
        mock_exchange.markets = {"BTC/USDT": {}}
        mock_ccxt.binance.return_value = mock_exchange

        await provider.initialize()

        assert provider._is_initialized is True
        assert provider._exchange is not None
        mock_exchange.load_markets.assert_called_once()

        await provider.shutdown()
        mock_exchange.close.assert_called_once()
        assert provider._is_initialized is False


@pytest.mark.asyncio
async def test_ccxt_provider_fetch_price(crypto_asset):
    """Test fetching price from CCXT"""
    provider = CCXTProvider(exchange_id="binance")

    # Mock exchange
    mock_exchange = AsyncMock()
    mock_exchange.load_markets = AsyncMock()
    mock_exchange.markets = {"BTC/USDT": {}}
    mock_exchange.fetch_ticker = AsyncMock(return_value={
        "last": 50000.0,
        "bid": 49990.0,
        "ask": 50010.0,
        "high": 51000.0,
        "low": 49000.0,
        "open": 49500.0,
        "close": 50000.0,
        "baseVolume": 100.0,
        "quoteVolume": 5000000.0,
        "change": 500.0,
        "percentage": 1.0,
        "timestamp": 1600000000000,
        "datetime": "2020-09-13T12:26:40.000Z",
        "info": {}
    })

    with patch("fiml.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        await provider.initialize()

        response = await provider.fetch_price(crypto_asset)

        assert response.provider == "ccxt_binance"
        assert response.asset == crypto_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 50000.0
        assert response.data["volume"] == 100.0
        assert response.is_valid is True

        mock_exchange.fetch_ticker.assert_called_with("BTC/USDT")


@pytest.mark.asyncio
async def test_ccxt_provider_fetch_ohlcv(crypto_asset):
    """Test fetching OHLCV from CCXT"""
    provider = CCXTProvider(exchange_id="binance")

    # Mock exchange
    mock_exchange = AsyncMock()
    mock_exchange.load_markets = AsyncMock()
    mock_exchange.markets = {"BTC/USDT": {}}
    mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
        [1600000000000, 49500.0, 51000.0, 49000.0, 50000.0, 100.0],
        [1600086400000, 50000.0, 52000.0, 49500.0, 51500.0, 120.0],
    ])

    with patch("fiml.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        await provider.initialize()

        response = await provider.fetch_ohlcv(crypto_asset, timeframe="1d")

        assert response.provider == "ccxt_binance"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["candles"]) == 2
        assert response.data["candles"][0]["close"] == 50000.0
        assert response.data["candles"][1]["close"] == 51500.0

        mock_exchange.fetch_ohlcv.assert_called_with("BTC/USDT", timeframe="1d", limit=100)


@pytest.mark.asyncio
async def test_ccxt_provider_supports_asset(crypto_asset, equity_asset):
    """Test asset support check"""
    provider = CCXTProvider(exchange_id="binance")

    # Mock exchange
    mock_exchange = AsyncMock()
    mock_exchange.load_markets = AsyncMock()
    mock_exchange.markets = {"BTC/USDT": {}}

    with patch("fiml.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        await provider.initialize()

        # Should support crypto if in markets
        assert await provider.supports_asset(crypto_asset) is True

        # Should not support equity
        assert await provider.supports_asset(equity_asset) is False

        # Should not support unknown crypto
        unknown_crypto = Asset(symbol="UNKNOWN", asset_type=AssetType.CRYPTO)
        assert await provider.supports_asset(unknown_crypto) is False


@pytest.mark.asyncio
async def test_ccxt_provider_error_handling(crypto_asset):
    """Test error handling in CCXT provider"""
    provider = CCXTProvider(exchange_id="binance")

    # Mock exchange
    mock_exchange = AsyncMock()
    mock_exchange.load_markets = AsyncMock()
    mock_exchange.markets = {"BTC/USDT": {}}

    with patch("fiml.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange

        # Define mock exception classes
        class MockNetworkError(Exception):
            pass

        class MockExchangeError(Exception):
            pass

        class MockRateLimitExceeded(Exception):
            pass

        class MockDDoSProtection(Exception):
            pass

        class MockOnMaintenance(Exception):
            pass

        class MockExchangeNotAvailable(Exception):
            pass

        class MockAuthenticationError(Exception):
            pass

        class MockRequestTimeout(Exception):
            pass

        mock_ccxt.NetworkError = MockNetworkError
        mock_ccxt.ExchangeError = MockExchangeError
        mock_ccxt.RateLimitExceeded = MockRateLimitExceeded
        mock_ccxt.DDoSProtection = MockDDoSProtection
        mock_ccxt.OnMaintenance = MockOnMaintenance
        mock_ccxt.ExchangeNotAvailable = MockExchangeNotAvailable
        mock_ccxt.AuthenticationError = MockAuthenticationError
        mock_ccxt.RequestTimeout = MockRequestTimeout

        await provider.initialize()

        # Test NetworkError
        mock_exchange.fetch_ticker.side_effect = MockNetworkError("Network error")
        with pytest.raises(ProviderTimeoutError):
            await provider.fetch_price(crypto_asset)

        # Test ExchangeError
        mock_exchange.fetch_ticker.side_effect = MockExchangeError("Exchange error")
        with pytest.raises(ProviderError):
            await provider.fetch_price(crypto_asset)

        # Test Geo-blocking
        mock_exchange.fetch_ticker.side_effect = MockExchangeError("Access denied from your country")
        with pytest.raises(RegionalRestrictionError):
            await provider.fetch_price(crypto_asset)


@pytest.mark.asyncio
async def test_ccxt_multi_exchange_provider(crypto_asset):
    """Test multi-exchange provider manager"""

    with patch("fiml.providers.ccxt_provider.CCXTProvider") as mock_provider_cls:
        # Setup mock providers
        mock_binance = AsyncMock()
        mock_coinbase = AsyncMock()

        def side_effect(exchange_id):
            if exchange_id == "binance":
                return mock_binance
            return mock_coinbase

        mock_provider_cls.side_effect = side_effect

        multi_provider = CCXTMultiExchangeProvider(exchanges=["binance", "coinbase"])

        # Test initialization
        await multi_provider.initialize_all()
        mock_binance.initialize.assert_called_once()
        mock_coinbase.initialize.assert_called_once()

        # Test fetch from all
        mock_binance.fetch_price.return_value = ProviderResponse(
            provider="ccxt_binance",
            asset=crypto_asset,
            data_type=DataType.PRICE,
            data={"price": 50000.0},
            timestamp=datetime.now(timezone.utc),
            is_valid=True
        )
        mock_coinbase.fetch_price.return_value = ProviderResponse(
            provider="ccxt_coinbase",
            asset=crypto_asset,
            data_type=DataType.PRICE,
            data={"price": 50100.0},
            timestamp=datetime.now(timezone.utc),
            is_valid=True
        )

        responses = await multi_provider.fetch_price_from_all(crypto_asset)
        assert len(responses) == 2

        # Test shutdown
        await multi_provider.shutdown_all()
        mock_binance.shutdown.assert_called_once()
        mock_coinbase.shutdown.assert_called_once()
