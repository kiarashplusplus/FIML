"""
Tests for Provider Cooldown Mechanism
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from fiml.arbitration.engine import DataArbitrationEngine
from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.base import BaseProvider, ProviderConfig


# Override fixtures to avoid Docker/Redis dependency
@pytest.fixture(scope="session", autouse=True)
def docker_services():
    yield

@pytest.fixture(autouse=True)
def reset_cache_singletons():
    yield

@pytest.fixture(autouse=True)
def init_session_db():
    yield

# Mock concrete provider for testing
class MockProvider(BaseProvider):
    async def initialize(self): pass
    async def shutdown(self): pass
    async def fetch_price(self, asset): pass
    async def fetch_ohlcv(self, asset, timeframe="1d", limit=100): pass
    async def fetch_fundamentals(self, asset): pass
    async def fetch_news(self, asset, limit=10): pass
    async def supports_asset(self, asset): return True
    async def get_health(self): pass

@pytest.fixture
def mock_provider():
    config = ProviderConfig(name="test_provider")
    provider = MockProvider(config)
    provider._is_initialized = True
    return provider

@pytest.fixture
def mock_asset():
    return Asset(symbol="AAPL", name="Apple Inc.", asset_type=AssetType.EQUITY)

def test_provider_cooldown_logic(mock_provider):
    """Test basic cooldown state logic"""
    assert not mock_provider.is_in_cooldown()
    assert mock_provider.is_enabled

    # Set cooldown for 60 seconds
    mock_provider.set_cooldown(60)
    assert mock_provider.is_in_cooldown()
    assert not mock_provider.is_enabled

    # Verify cooldown timestamp
    assert mock_provider._cooldown_until > datetime.now(timezone.utc)

def test_provider_cooldown_expiry(mock_provider):
    """Test that cooldown expires correctly"""
    # Set short cooldown
    mock_provider.set_cooldown(-1) # Already expired
    assert not mock_provider.is_in_cooldown()
    assert mock_provider.is_enabled

@pytest.mark.asyncio
async def test_arbitration_skips_cooldown_provider(mock_provider, mock_asset):
    """Test that arbitration engine gives 0 score to cooldown provider"""
    engine = DataArbitrationEngine()

    # Put provider in cooldown
    mock_provider.set_cooldown(60)

    score = await engine._score_provider(
        mock_provider,
        mock_asset,
        DataType.PRICE,
        "US",
        300
    )

    assert score.total == 0.0

@pytest.mark.asyncio
async def test_arbitration_triggers_cooldown(mock_provider, mock_asset):
    """Test that rate limit errors trigger cooldown"""
    engine = DataArbitrationEngine()

    # Mock provider to raise rate limit error
    mock_provider.fetch_price = AsyncMock(side_effect=Exception("Rate limit exceeded. Wait 10s"))

    # Mock registry to return our provider
    engine.provider_registry = Mock()
    engine.provider_registry.providers = {"test_provider": mock_provider}

    # Create a plan that uses this provider
    plan = Mock()
    plan.primary_provider = "test_provider"
    plan.fallback_providers = []

    import contextlib
    with contextlib.suppress(Exception):
        await engine.execute_with_fallback(plan, mock_asset, DataType.PRICE)

    # Verify cooldown was set
    assert mock_provider.is_in_cooldown()
    # Should be around 11 seconds (10s + 1s buffer)
    # We can't easily check exact time, but we can check it's set
    assert mock_provider._cooldown_until is not None
