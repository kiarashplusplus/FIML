"""
Benchmark configuration and fixtures
"""

import pytest
from fiml.core.config import Settings
from fiml.core.models import Asset, AssetType, Market


@pytest.fixture
def benchmark_settings():
    """Settings for benchmarks"""
    return Settings(
        fiml_env="development",
        redis_host="localhost",
        postgres_host="localhost",
        enable_compliance_checks=False,
        enable_rate_limiting=False,
    )


@pytest.fixture
def benchmark_asset():
    """Standard asset for benchmarks"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US,
        exchange="NASDAQ",
        currency="USD",
    )


@pytest.fixture
def benchmark_crypto_asset():
    """Standard crypto asset for benchmarks"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
        market=Market.CRYPTO,
        exchange="binance",
        currency="USDT",
    )
