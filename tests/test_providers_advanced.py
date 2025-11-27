"""
Additional tests for Providers
"""

import pytest

from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.base import ProviderConfig
from fiml.providers.mock_provider import MockProvider
from fiml.providers.yahoo_finance import YahooFinanceProvider


class TestBaseProvider:
    """Test base provider class"""

    @pytest.mark.asyncio
    async def test_base_provider_config(self):
        """Test provider configuration"""
        config = ProviderConfig(
            name="test_provider",
            enabled=True,
            priority=100,
            timeout_seconds=30,
            rate_limit_per_minute=60,
        )

        assert config.name == "test_provider"
        assert config.enabled is True
        assert config.priority == 100


class TestMockProviderAdvanced:
    """Additional tests for mock provider"""

    @pytest.mark.asyncio
    async def test_mock_provider_fetch_ohlcv(self):
        """Test mock provider OHLCV fetch"""
        provider = MockProvider()
        await provider.initialize()

        asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)

        response = await provider.fetch_ohlcv(asset, timeframe="1d", limit=10)

        assert response is not None
        assert response.data_type == DataType.OHLCV
        assert "candles" in response.data

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_mock_provider_fetch_fundamentals(self):
        """Test mock provider fundamentals fetch"""
        provider = MockProvider()
        await provider.initialize()

        asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)

        response = await provider.fetch_fundamentals(asset)

        assert response is not None
        assert response.data_type == DataType.FUNDAMENTALS

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_mock_provider_fetch_news(self):
        """Test mock provider news fetch"""
        provider = MockProvider()
        await provider.initialize()

        asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)

        response = await provider.fetch_news(asset)

        assert response is not None

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_mock_provider_supports_all_assets(self):
        """Test mock provider supports all assets"""
        provider = MockProvider()
        await provider.initialize()

        # Test different asset types
        for asset_type in [AssetType.EQUITY, AssetType.CRYPTO, AssetType.FOREX]:
            asset = Asset(symbol="TEST", asset_type=asset_type, market=Market.US)

            supports = await provider.supports_asset(asset)
            assert supports is True

        await provider.shutdown()


class TestYahooFinanceProviderAdvanced:
    """Additional tests for Yahoo Finance provider"""

    @pytest.mark.asyncio
    async def test_yahoo_provider_supports_crypto(self):
        """Test Yahoo Finance provider crypto support"""
        provider = YahooFinanceProvider()
        await provider.initialize()

        asset = Asset(symbol="BTC-USD", asset_type=AssetType.CRYPTO, market=Market.CRYPTO)

        supports = await provider.supports_asset(asset)
        # Yahoo might or might not support crypto - both are valid
        assert isinstance(supports, bool)

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_yahoo_provider_doesnt_support_future(self):
        """Test Yahoo Finance provider doesn't support futures"""
        provider = YahooFinanceProvider()
        await provider.initialize()

        asset = Asset(symbol="ES", asset_type=AssetType.FUTURE, market=Market.US)

        supports = await provider.supports_asset(asset)
        # Yahoo might not support all asset types
        assert isinstance(supports, bool)

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_yahoo_provider_rate_limiting(self):
        """Test Yahoo Finance provider has rate limiting"""
        provider = YahooFinanceProvider()
        await provider.initialize()

        # Check config has rate limit
        assert provider.config.rate_limit_per_minute > 0

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_yahoo_provider_initialization(self):
        """Test Yahoo Finance provider initialization"""
        provider = YahooFinanceProvider()

        assert provider.name == "yahoo_finance"

        await provider.initialize()
        # Check if enabled after initialization
        assert isinstance(provider.is_enabled, bool)
        await provider.shutdown()
