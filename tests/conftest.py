"""
Test configuration for FIML
"""

import pytest
from fiml.core.config import Settings


def pytest_addoption(parser):
    """Add custom command-line options"""
    parser.addoption(
        "--run-cache-tests",
        action="store_true",
        default=False,
        help="Run tests that require Redis/PostgreSQL cache backends"
    )


@pytest.fixture
def test_settings():
    """Test settings fixture"""
    return Settings(
        fiml_env="development",
        redis_host="localhost",
        postgres_host="localhost",
        enable_compliance_checks=False,
        enable_rate_limiting=False,
    )


@pytest.fixture
def mock_asset():
    """Mock asset fixture"""
    from fiml.core.models import Asset, AssetType, Market

    return Asset(
        symbol="TSLA",
        name="Tesla Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US,
        exchange="NASDAQ",
        currency="USD",
    )

