"""
Tests for Yahoo Finance Provider
"""

from unittest.mock import patch

import pandas as pd
import pytest

from fiml.core.exceptions import ProviderError
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.yahoo_finance import YahooFinanceProvider


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
async def test_yahoo_provider_initialization():
    """Test Yahoo Finance provider initialization"""
    provider = YahooFinanceProvider()

    assert provider.name == "yahoo_finance"
    assert provider._is_initialized is False

    await provider.initialize()
    assert provider._is_initialized is True

    await provider.shutdown()
    assert provider._is_initialized is False


@pytest.mark.asyncio
async def test_yahoo_provider_fetch_price(equity_asset):
    """Test fetching price from Yahoo Finance"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    # Mock yfinance Ticker
    with patch("fiml.providers.yahoo_finance.yf.Ticker") as MockTicker:
        mock_instance = MockTicker.return_value
        mock_instance.info = {
            "currentPrice": 150.0,
            "regularMarketChange": 2.5,
            "regularMarketChangePercent": 1.6,
            "volume": 1000000,
            "marketCap": 2000000000000,
            "previousClose": 147.5,
        }

        response = await provider.fetch_price(equity_asset)

        assert response.provider == "yahoo_finance"
        assert response.asset == equity_asset
        assert response.data_type == DataType.PRICE
        assert response.data["price"] == 150.0
        assert response.data["change"] == 2.5
        assert response.is_valid is True

        MockTicker.assert_called_with("AAPL")


@pytest.mark.asyncio
async def test_yahoo_provider_fetch_ohlcv(equity_asset):
    """Test fetching OHLCV from Yahoo Finance"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    # Mock yfinance Ticker
    with patch("fiml.providers.yahoo_finance.yf.Ticker") as MockTicker:
        mock_instance = MockTicker.return_value

        # Create mock history DataFrame
        dates = pd.date_range(start="2023-01-01", periods=2)
        mock_df = pd.DataFrame({
            "Open": [148.0, 150.0],
            "High": [152.0, 155.0],
            "Low": [147.0, 149.0],
            "Close": [150.0, 153.0],
            "Volume": [1000000, 1200000]
        }, index=dates)

        mock_instance.history.return_value = mock_df

        response = await provider.fetch_ohlcv(equity_asset, timeframe="1d")

        assert response.provider == "yahoo_finance"
        assert response.data_type == DataType.OHLCV
        assert len(response.data["candles"]) == 2
        assert response.data["candles"][0]["close"] == 150.0
        assert response.data["candles"][1]["close"] == 153.0

        mock_instance.history.assert_called_with(period="100d", interval="1d")


@pytest.mark.asyncio
async def test_yahoo_provider_fetch_fundamentals(equity_asset):
    """Test fetching fundamentals from Yahoo Finance"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    # Mock yfinance Ticker
    with patch("fiml.providers.yahoo_finance.yf.Ticker") as MockTicker:
        mock_instance = MockTicker.return_value
        mock_instance.info = {
            "marketCap": 2000000000000,
            "trailingPE": 25.5,
            "forwardPE": 22.0,
            "sector": "Technology",
        }

        response = await provider.fetch_fundamentals(equity_asset)

        assert response.provider == "yahoo_finance"
        assert response.data_type == DataType.FUNDAMENTALS
        assert response.data["market_cap"] == 2000000000000
        assert response.data["pe_ratio"] == 25.5
        assert response.data["sector"] == "Technology"


@pytest.mark.asyncio
async def test_yahoo_provider_fetch_news(equity_asset):
    """Test fetching news from Yahoo Finance"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    # Mock yfinance Ticker
    with patch("fiml.providers.yahoo_finance.yf.Ticker") as MockTicker:
        mock_instance = MockTicker.return_value
        mock_instance.news = [
            {
                "title": "Apple releases new iPhone",
                "link": "https://example.com/news",
                "publisher": "Tech News",
                "providerPublishTime": 1672531200,
                "type": "STORY"
            }
        ]

        response = await provider.fetch_news(equity_asset)

        assert response.provider == "yahoo_finance"
        assert response.data_type == DataType.NEWS
        assert len(response.data["articles"]) == 1
        assert response.data["articles"][0]["title"] == "Apple releases new iPhone"


@pytest.mark.asyncio
async def test_yahoo_provider_supports_asset(equity_asset, crypto_asset):
    """Test asset support check"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    # Should support equity
    assert await provider.supports_asset(equity_asset) is True

    # Should NOT support crypto (based on current implementation)
    assert await provider.supports_asset(crypto_asset) is False


@pytest.mark.asyncio
async def test_yahoo_provider_error_handling(equity_asset):
    """Test error handling in Yahoo Finance provider"""
    provider = YahooFinanceProvider()
    await provider.initialize()

    # Mock yfinance Ticker to raise exception
    with patch("fiml.providers.yahoo_finance.yf.Ticker") as mock_ticker:
        mock_ticker.side_effect = Exception("API Error")

        with pytest.raises(ProviderError):
            await provider.fetch_price(equity_asset)

        with pytest.raises(ProviderError):
            await provider.fetch_ohlcv(equity_asset)
