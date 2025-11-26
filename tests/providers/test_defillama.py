"""
Tests for DefiLlama Provider
"""

import pytest

from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.defillama import DefiLlamaProvider


@pytest.fixture
def crypto_asset():
    """Create a crypto asset for testing"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
    )


@pytest.fixture
def defi_asset():
    """Create a DeFi asset for testing"""
    return Asset(
        symbol="AAVE",
        name="Aave",
        asset_type=AssetType.CRYPTO,
    )


@pytest.mark.asyncio
async def test_defillama_provider_initialization():
    """Test DefiLlama provider initialization (no API key required)"""
    provider = DefiLlamaProvider()

    assert provider.name == "defillama"
    assert provider.config.enabled is True
    assert provider.config.priority == 5
    assert provider._is_initialized is False
    assert not provider.is_enabled  # Not initialized yet

    await provider.initialize()

    assert provider._is_initialized is True
    assert provider._session is not None
    assert provider.is_enabled

    await provider.shutdown()

    assert provider._is_initialized is False
    assert not provider.is_enabled


@pytest.mark.asyncio
async def test_defillama_provider_supports_crypto(crypto_asset):
    """Test DefiLlama provider supports crypto assets"""
    provider = DefiLlamaProvider()
    await provider.initialize()

    supports = await provider.supports_asset(crypto_asset)
    assert supports is True

    await provider.shutdown()


@pytest.mark.asyncio
async def test_defillama_provider_does_not_support_equity():
    """Test DefiLlama provider does not support equity assets"""
    provider = DefiLlamaProvider()
    await provider.initialize()

    equity_asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )

    supports = await provider.supports_asset(equity_asset)
    assert supports is False

    await provider.shutdown()


@pytest.mark.asyncio
async def test_defillama_fetch_news(crypto_asset):
    """Test DefiLlama news endpoint returns empty (not supported)"""
    provider = DefiLlamaProvider()
    await provider.initialize()

    response = await provider.fetch_news(crypto_asset)

    assert response is not None
    assert response.provider == "defillama"
    assert response.data_type == DataType.NEWS
    assert response.data["articles"] == []
    assert response.is_fresh is False
    assert response.confidence == 0.0

    await provider.shutdown()


@pytest.mark.asyncio
async def test_defillama_get_health():
    """Test DefiLlama provider health check"""
    provider = DefiLlamaProvider()
    await provider.initialize()

    health = await provider.get_health()

    assert health is not None
    assert health.provider_name == "defillama"
    assert health.is_healthy is True
    assert health.uptime_percent == 0.98
    assert health.avg_latency_ms == 250.0

    await provider.shutdown()


@pytest.mark.asyncio
async def test_defillama_symbol_mapping():
    """Test DefiLlama symbol to coin ID mapping"""
    provider = DefiLlamaProvider()

    # Test direct mapping
    assert provider._get_coin_id("BTC") == "coingecko:bitcoin"
    assert provider._get_coin_id("ETH") == "coingecko:ethereum"
    assert provider._get_coin_id("SOL") == "coingecko:solana"

    # Test case insensitivity
    assert provider._get_coin_id("btc") == "coingecko:bitcoin"
    assert provider._get_coin_id("Eth") == "coingecko:ethereum"

    # Test trading pair suffix stripping
    assert provider._get_coin_id("BTCUSDT") == "coingecko:bitcoin"
    assert provider._get_coin_id("ETHBUSD") == "coingecko:ethereum"

    # Test unknown symbols (should return lowercase with coingecko prefix)
    assert provider._get_coin_id("UNKNOWN") == "coingecko:unknown"


@pytest.mark.asyncio
async def test_defillama_provider_config():
    """Test DefiLlama provider configuration"""
    provider = DefiLlamaProvider()

    assert provider.config.name == "defillama"
    assert provider.config.enabled is True
    assert provider.config.priority == 5  # Lower than CoinGecko as fallback
    assert provider.config.rate_limit_per_minute == 100
    assert provider.config.timeout_seconds == 10
    assert provider.config.api_key is None  # No API key required


@pytest.mark.asyncio
async def test_defillama_provider_api_urls():
    """Test DefiLlama provider API URL configuration"""
    provider = DefiLlamaProvider()

    assert provider.COINS_BASE_URL == "https://coins.llama.fi"
    assert provider.TVL_BASE_URL == "https://api.llama.fi"


@pytest.mark.asyncio
async def test_defillama_get_coin_id_defi_tokens():
    """Test DefiLlama symbol mapping for DeFi tokens"""
    provider = DefiLlamaProvider()

    # Test DeFi-specific tokens
    assert provider._get_coin_id("AAVE") == "coingecko:aave"
    assert provider._get_coin_id("UNI") == "coingecko:uniswap"
    assert provider._get_coin_id("MKR") == "coingecko:maker"
    assert provider._get_coin_id("CRV") == "coingecko:curve-dao-token"
    assert provider._get_coin_id("LDO") == "coingecko:lido-dao"

    # Test Layer 2 tokens
    assert provider._get_coin_id("ARB") == "coingecko:arbitrum"
    assert provider._get_coin_id("OP") == "coingecko:optimism"
    assert provider._get_coin_id("AVAX") == "coingecko:avalanche-2"


@pytest.mark.asyncio
async def test_defillama_success_rate():
    """Test DefiLlama provider success rate tracking"""
    provider = DefiLlamaProvider()
    await provider.initialize()

    # Initial success rate should be 1.0
    success_rate = await provider.get_success_rate()
    assert success_rate == 1.0

    # Simulate requests
    provider._request_count = 10
    provider._error_count = 2

    success_rate = await provider.get_success_rate()
    assert success_rate == 0.8

    await provider.shutdown()


@pytest.mark.asyncio
async def test_defillama_request_recording():
    """Test DefiLlama provider request recording"""
    provider = DefiLlamaProvider()
    await provider.initialize()

    assert provider._request_count == 0
    assert provider._error_count == 0

    provider._record_request()
    assert provider._request_count == 1
    assert provider._last_request_time is not None

    provider._record_error()
    assert provider._error_count == 1

    await provider.shutdown()
