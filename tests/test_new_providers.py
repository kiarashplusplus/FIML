"""
Tests for new providers (Polygon, Finnhub, Twelvedata, etc.)
"""

import pytest

from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.polygon import PolygonProvider
from fiml.providers.finnhub import FinnhubProvider
from fiml.providers.twelvedata import TwelvedataProvider
from fiml.providers.tiingo import TiingoProvider
from fiml.providers.intrinio import IntrinioProvider
from fiml.providers.marketstack import MarketstackProvider
from fiml.providers.coingecko import CoinGeckoProvider
from fiml.providers.coinmarketcap import CoinMarketCapProvider
from fiml.providers.quandl import QuandlProvider


@pytest.mark.asyncio
async def test_polygon_provider_initialization():
    """Test Polygon provider initialization with test API key"""
    provider = PolygonProvider(api_key="test_key")
    assert provider.name == "polygon"
    assert provider.config.priority == 8
    assert not provider.is_enabled  # Not initialized yet


@pytest.mark.asyncio
async def test_finnhub_provider_initialization():
    """Test Finnhub provider initialization with test API key"""
    provider = FinnhubProvider(api_key="test_key")
    assert provider.name == "finnhub"
    assert provider.config.priority == 7
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_twelvedata_provider_initialization():
    """Test Twelvedata provider initialization with test API key"""
    provider = TwelvedataProvider(api_key="test_key")
    assert provider.name == "twelvedata"
    assert provider.config.priority == 7
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_tiingo_provider_initialization():
    """Test Tiingo provider initialization with test API key"""
    provider = TiingoProvider(api_key="test_key")
    assert provider.name == "tiingo"
    assert provider.config.priority == 7
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_intrinio_provider_initialization():
    """Test Intrinio provider initialization with test API key"""
    provider = IntrinioProvider(api_key="test_key")
    assert provider.name == "intrinio"
    assert provider.config.priority == 7
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_marketstack_provider_initialization():
    """Test Marketstack provider initialization with test API key"""
    provider = MarketstackProvider(api_key="test_key")
    assert provider.name == "marketstack"
    assert provider.config.priority == 6
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_coingecko_provider_initialization():
    """Test CoinGecko provider initialization (no API key required)"""
    provider = CoinGeckoProvider()
    assert provider.name == "coingecko"
    assert provider.config.priority == 6
    assert not provider.is_enabled  # Not initialized yet
    
    await provider.initialize()
    assert provider.is_enabled
    
    await provider.shutdown()
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_coinmarketcap_provider_initialization():
    """Test CoinMarketCap provider initialization with test API key"""
    provider = CoinMarketCapProvider(api_key="test_key")
    assert provider.name == "coinmarketcap"
    assert provider.config.priority == 7
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_quandl_provider_initialization():
    """Test Quandl provider initialization with test API key"""
    provider = QuandlProvider(api_key="test_key")
    assert provider.name == "quandl"
    assert provider.config.priority == 6
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_polygon_supports_equity():
    """Test Polygon provider supports equity"""
    provider = PolygonProvider(api_key="test_key")
    
    asset = Asset(
        symbol="AAPL",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )
    
    supports = await provider.supports_asset(asset)
    assert supports is True


@pytest.mark.asyncio
async def test_polygon_supports_crypto():
    """Test Polygon provider supports crypto"""
    provider = PolygonProvider(api_key="test_key")
    
    asset = Asset(
        symbol="BTC",
        asset_type=AssetType.CRYPTO,
        market=Market.US,
    )
    
    supports = await provider.supports_asset(asset)
    assert supports is True


@pytest.mark.asyncio
async def test_finnhub_supports_equity():
    """Test Finnhub provider supports equity"""
    provider = FinnhubProvider(api_key="test_key")
    
    asset = Asset(
        symbol="AAPL",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )
    
    supports = await provider.supports_asset(asset)
    assert supports is True


@pytest.mark.asyncio
async def test_coingecko_supports_crypto():
    """Test CoinGecko provider supports crypto"""
    provider = CoinGeckoProvider()
    
    asset = Asset(
        symbol="BTC",
        asset_type=AssetType.CRYPTO,
        market=Market.US,
    )
    
    supports = await provider.supports_asset(asset)
    assert supports is True


@pytest.mark.asyncio
async def test_coingecko_does_not_support_equity():
    """Test CoinGecko provider does not support equity"""
    provider = CoinGeckoProvider()
    
    asset = Asset(
        symbol="AAPL",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )
    
    supports = await provider.supports_asset(asset)
    assert supports is False


@pytest.mark.asyncio
async def test_coinmarketcap_supports_crypto():
    """Test CoinMarketCap provider supports crypto"""
    provider = CoinMarketCapProvider(api_key="test_key")
    
    asset = Asset(
        symbol="BTC",
        asset_type=AssetType.CRYPTO,
        market=Market.US,
    )
    
    supports = await provider.supports_asset(asset)
    assert supports is True


@pytest.mark.asyncio
async def test_twelvedata_supports_multiple_asset_types():
    """Test Twelvedata provider supports multiple asset types"""
    provider = TwelvedataProvider(api_key="test_key")
    
    equity_asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)
    forex_asset = Asset(symbol="EUR/USD", asset_type=AssetType.FOREX, market=Market.US)
    crypto_asset = Asset(symbol="BTC", asset_type=AssetType.CRYPTO, market=Market.US)
    
    assert await provider.supports_asset(equity_asset) is True
    assert await provider.supports_asset(forex_asset) is True
    assert await provider.supports_asset(crypto_asset) is True


@pytest.mark.asyncio
async def test_tiingo_supports_equity_and_etf():
    """Test Tiingo provider supports equity and ETF"""
    provider = TiingoProvider(api_key="test_key")
    
    equity_asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)
    etf_asset = Asset(symbol="SPY", asset_type=AssetType.ETF, market=Market.US)
    
    assert await provider.supports_asset(equity_asset) is True
    assert await provider.supports_asset(etf_asset) is True


@pytest.mark.asyncio
async def test_provider_health_reporting():
    """Test provider health reporting"""
    provider = CoinGeckoProvider()
    await provider.initialize()
    
    health = await provider.get_health()
    
    assert health is not None
    assert health.provider_name == "coingecko"
    assert health.is_healthy is True
    assert health.uptime_percent > 0.0
    
    await provider.shutdown()
