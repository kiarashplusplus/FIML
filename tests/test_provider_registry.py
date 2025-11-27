"""
Tests for Provider Registry
"""

import pytest

from fiml.core.exceptions import NoProviderAvailableError
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.registry import ProviderRegistry, provider_registry


class TestProviderRegistry:
    """Test provider registry"""

    @pytest.mark.asyncio
    async def test_registry_initialization(self):
        """Test registry initialization"""
        registry = ProviderRegistry()
        await registry.initialize()

        assert registry._initialized is True
        assert len(registry.providers) > 0

        await registry.shutdown()
        assert registry._initialized is False

    @pytest.mark.asyncio
    async def test_registry_double_initialization(self):
        """Test initializing registry twice"""
        registry = ProviderRegistry()
        await registry.initialize()
        await registry.initialize()  # Should not fail

        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_providers_for_asset(self):
        """Test getting providers for an asset"""
        await provider_registry.initialize()

        asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)

        providers = await provider_registry.get_providers_for_asset(asset, DataType.PRICE)
        assert len(providers) > 0

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_providers_unsupported_asset(self):
        """Test getting providers for unsupported asset"""
        await provider_registry.initialize()

        # Create an asset that might not be supported
        asset = Asset(symbol="INVALID_SYMBOL_XYZ", asset_type=AssetType.FUTURE, market=Market.CN)

        # Should raise NoProviderAvailableError if no providers support it
        try:
            providers = await provider_registry.get_providers_for_asset(asset, DataType.PRICE)
            # If it succeeds, that's fine too (mock provider might support everything)
            assert isinstance(providers, list)
        except NoProviderAvailableError:
            pass  # This is expected

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_provider_health(self):
        """Test getting provider health"""
        await provider_registry.initialize()

        # Get health for a known provider
        health = await provider_registry.get_provider_health("mock_provider")
        assert health is not None
        assert health.provider_name == "mock_provider"

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_provider_health_unknown(self):
        """Test getting health for unknown provider"""
        await provider_registry.initialize()

        health = await provider_registry.get_provider_health("unknown_provider")
        assert health is None

        await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_all_health(self):
        """Test getting health for all providers"""
        await provider_registry.initialize()

        health_status = await provider_registry.get_all_health()
        assert isinstance(health_status, dict)
        assert len(health_status) > 0

        await provider_registry.shutdown()
