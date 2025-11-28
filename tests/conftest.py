"""
Test configuration for FIML
"""

import contextlib
import os
import subprocess
import time
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg2
import pytest
import redis
from dotenv import load_dotenv

# Load .env file first to get real configuration
load_dotenv()

from fiml.core.config import Settings  # noqa: E402

# Set environment variables BEFORE any imports happen
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "fiml_test"
os.environ["POSTGRES_USER"] = "fiml_test"
os.environ["POSTGRES_PASSWORD"] = "fiml_test_password"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["FIML_ENV"] = "test"

# Mock Azure OpenAI configuration for tests (unless already set in .env)
# When using mock endpoint, httpx calls are automatically mocked by the
# mock_azure_openai_httpx fixture to prevent timeouts from unreachable endpoints
if "AZURE_OPENAI_ENDPOINT" not in os.environ:
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-azure-openai.openai.azure.com/"
if "AZURE_OPENAI_API_KEY" not in os.environ:
    os.environ["AZURE_OPENAI_API_KEY"] = "mock-api-key-for-testing"
if "AZURE_OPENAI_DEPLOYMENT_NAME" not in os.environ:
    os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "gpt-4"
if "AZURE_OPENAI_API_VERSION" not in os.environ:
    os.environ["AZURE_OPENAI_API_VERSION"] = "2024-02-15-preview"


def pytest_configure(config):
    """Pytest configuration hook - runs before test collection"""
    # Clear settings cache to ensure our environment variables are used
    from fiml.core import config as config_module

    if hasattr(config_module, "get_settings"):
        config_module.get_settings.cache_clear()
        # Reload global settings
        config_module.settings = config_module.get_settings()


def pytest_addoption(parser):
    """Add custom command-line options"""
    parser.addoption(
        "--run-cache-tests",
        action="store_true",
        default=False,
        help="Run tests that require Redis/PostgreSQL cache backends",
    )
    parser.addoption(
        "--no-docker",
        action="store_true",
        default=False,
        help="Skip Docker container startup (assume services are already running)",
    )


def is_redis_ready(host="localhost", port=6379, max_retries=30):
    """Check if Redis is ready"""
    for i in range(max_retries):
        try:
            r = redis.Redis(host=host, port=port, socket_connect_timeout=1)
            r.ping()
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            if i < max_retries - 1:
                time.sleep(1)
    return False


def is_postgres_ready(host="localhost", port=5432, max_retries=30):
    """Check if PostgreSQL is ready"""
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database="fiml_test",
                user="fiml_test",
                password="fiml_test_password",
                connect_timeout=1,
            )
            conn.close()
            return True
        except psycopg2.OperationalError:
            if i < max_retries - 1:
                time.sleep(1)
    return False


@pytest.fixture(scope="session", autouse=True)
def docker_services(request):
    """Start Docker services for testing"""
    no_docker = request.config.getoption("--no-docker")

    if no_docker:
        # Assume services are already running
        if not is_redis_ready():
            pytest.exit("Redis is not available. Please start Redis or remove --no-docker flag.")
        if not is_postgres_ready():
            pytest.exit(
                "PostgreSQL is not available. Please start PostgreSQL or remove --no-docker flag."
            )
        yield
        return

    # Check if docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.exit("Docker is not available. Install Docker or use --no-docker flag.")

    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compose_file = os.path.join(project_root, "docker-compose.test.yml")

    if not os.path.exists(compose_file):
        pytest.exit(f"docker-compose.test.yml not found at {compose_file}")

    # Start services
    print("\n🐳 Starting test containers (Redis & PostgreSQL)...")
    subprocess.run(
        ["sudo", "docker", "compose", "-f", compose_file, "up", "-d"],
        cwd=project_root,
        check=True,
        capture_output=True,
    )

    # Wait for services to be ready
    print("⏳ Waiting for Redis to be ready...")
    if not is_redis_ready():
        subprocess.run(
            ["sudo", "docker", "compose", "-f", compose_file, "down", "-v"], cwd=project_root
        )
        pytest.exit("Redis failed to start within timeout period")
    print("✅ Redis is ready")

    print("⏳ Waiting for PostgreSQL to be ready...")
    if not is_postgres_ready():
        subprocess.run(
            ["sudo", "docker", "compose", "-f", compose_file, "down", "-v"], cwd=project_root
        )
        pytest.exit("PostgreSQL failed to start within timeout period")
    print("✅ PostgreSQL is ready")

    print("✅ All test services are ready\n")

    yield

    # Teardown: stop and remove containers
    print("\n🧹 Cleaning up test containers...")
    subprocess.run(
        ["sudo", "docker", "compose", "-f", compose_file, "down", "-v"],
        cwd=project_root,
        capture_output=True,
    )
    print("✅ Test containers cleaned up\n")


@pytest.fixture
def test_settings():
    """Test settings fixture"""
    return Settings(
        fiml_env="test",
        redis_host="localhost",
        redis_port=6379,
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="fiml_test",
        postgres_user="fiml_test",
        postgres_password="fiml_test_password",
        enable_compliance_checks=False,
        enable_rate_limiting=False,
        # Mock Azure OpenAI configuration
        azure_openai_endpoint="https://mock-azure-openai.openai.azure.com/",
        azure_openai_api_key="mock-api-key-for-testing",
        azure_openai_deployment_name="gpt-4",
        azure_openai_api_version="2024-02-15-preview",
    )


@pytest.fixture(autouse=True)
def mock_azure_openai_httpx():
    """
    Automatically mock httpx calls to Azure OpenAI when using mock endpoint.

    This prevents tests from making actual HTTP calls to the non-existent
    mock endpoint (https://mock-azure-openai.openai.azure.com/), which would
    cause timeouts and slow down tests significantly.

    The fixture is autouse=True, so it applies to all tests automatically
    when the mock endpoint is configured.

    NOTE: This only mocks calls to the Azure OpenAI endpoint, not all httpx calls.
    """
    # Force mock endpoint for non-live tests
    from fiml.core.config import settings
    
    mock_endpoint = "https://mock-azure-openai.openai.azure.com/"
    
    # Patch settings to use mock endpoint
    with patch.object(settings, "azure_openai_endpoint", mock_endpoint):
        # Create a mock response that mimics Azure OpenAI's response format
        # Create a mock response that mimics Azure OpenAI's response format
        mock_openai_response = MagicMock()
        mock_openai_response.status_code = 200
        mock_openai_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a mock response from Azure OpenAI for testing purposes. This is educational content and not financial advice.",
                    },
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

        # Store the original post method to use for non-Azure OpenAI calls
        original_post = None

        async def selective_mock_post(self, url, *args, **kwargs):
            """Only mock Azure OpenAI calls, pass through others"""
            url_str = str(url)
            # Check if this is an Azure OpenAI call using proper URL parsing
            # to prevent URL substring attacks (e.g., evil.com?q=openai.azure.com)
            # Use proper URL parsing to check the hostname
            from urllib.parse import urlparse

            try:
                parsed = urlparse(url_str)
                hostname = parsed.hostname or ""
                # Check for Azure OpenAI domains using proper domain matching:
                # Must be exactly "openai.azure.com" or a subdomain like "x.openai.azure.com"
                # The hostname must end with ".openai.azure.com" with a dot before it,
                # OR be exactly "openai.azure.com"
                is_azure_domain = hostname == "openai.azure.com" or (
                    len(hostname) > len(".openai.azure.com")
                    and hostname[-(len(".openai.azure.com")) :] == ".openai.azure.com"
                )
                is_azure_openai = is_azure_domain
            except Exception:
                is_azure_openai = False

            if is_azure_openai:
                return mock_openai_response
            # For all other calls, use the original method
            if original_post is not None:
                return await original_post(self, url, *args, **kwargs)
            # Fallback for cases where original wasn't captured
            raise RuntimeError(f"Unmocked httpx call to: {url_str}")

        # Get the original method before patching
        import httpx

        original_post = httpx.AsyncClient.post

        # Patch with our selective mock
        with patch.object(httpx.AsyncClient, "post", selective_mock_post):
            yield


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


@pytest.fixture(scope="session")
async def init_session_db():
    """Initialize session database tables for testing"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from fiml.core.config import settings
    from fiml.sessions.db import CREATE_TABLES_SQL

    # Create engine
    engine = create_async_engine(settings.database_url, echo=False)

    try:
        async with engine.begin() as conn:
            # First, drop existing tables if they exist (clean slate)
            await conn.execute(text("DROP TABLE IF EXISTS session_metrics CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE"))

            # Then create tables with new schema
            statements = CREATE_TABLES_SQL.strip().split(";")
            for statement in statements:
                statement = statement.strip()
                if statement:
                    await conn.execute(text(statement))
    finally:
        await engine.dispose()

    yield

    # Cleanup: drop tables after tests
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS session_metrics CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE"))
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
def reset_cache_singletons():
    """
    Reset cache singletons after each test to prevent test pollution.

    Some tests mock the global l1_cache and cache_manager singletons,
    which can pollute other tests. This fixture captures the initial state
    and restores it after each test.
    """
    from fiml.cache.l1_cache import l1_cache
    from fiml.cache.l2_cache import l2_cache
    from fiml.cache.manager import cache_manager

    # Capture initial state before test
    initial_l1_initialized = l1_cache._initialized
    initial_l1_redis = l1_cache._redis
    initial_l2_initialized = l2_cache._initialized
    initial_cm_initialized = cache_manager._initialized

    yield

    # Restore state after test if it was corrupted by mocking
    # Check if _redis was changed to a different object (mock or otherwise)
    redis_was_changed = (initial_l1_redis is None and l1_cache._redis is not None) or (
        initial_l1_redis is not None and l1_cache._redis is not initial_l1_redis
    )

    if l1_cache._initialized and redis_was_changed:
        # The cache was mocked - reset to initial state
        l1_cache._redis = initial_l1_redis
        l1_cache._initialized = initial_l1_initialized
        l1_cache._access_counts.clear()
        l1_cache._last_access.clear()

    # Also check if _initialized was set without proper initialization
    if l1_cache._initialized and l1_cache._redis is None:
        l1_cache._initialized = False

    # Reset L2 cache if polluted
    if l2_cache._initialized != initial_l2_initialized and l2_cache._engine is None:
        l2_cache._initialized = initial_l2_initialized

    # Reset cache manager if L1 was reset
    if cache_manager._initialized != initial_cm_initialized:
        cache_manager._initialized = initial_cm_initialized


@pytest.fixture(autouse=True)
def mock_yfinance_network_calls(request):
    """
    Mock yfinance network calls to prevent tests from making real HTTP requests.

    This fixture is autouse=True, so it applies to all tests automatically,
    preventing Yahoo Finance API calls during testing. Tests that need real
    API calls should use the @pytest.mark.live marker.
    """
    # Skip mocking for live tests
    if "live" in request.keywords:
        yield
        return
    # Create mock data for yfinance
    mock_info = {
        "currentPrice": 150.25,
        "regularMarketChange": 2.50,
        "regularMarketChangePercent": 1.69,
        "volume": 50000000,
        "marketCap": 2500000000000,
        "previousClose": 147.75,
        "trailingPE": 28.5,
        "forwardPE": 25.2,
        "pegRatio": 2.1,
        "priceToBook": 45.6,
        "trailingEps": 5.28,
        "beta": 1.2,
        "dividendYield": 0.005,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "fullTimeEmployees": 150000,
        "fiftyTwoWeekHigh": 180.0,
        "fiftyTwoWeekLow": 120.0,
    }

    mock_history_data = {
        "Open": [150.0, 151.0, 152.0],
        "High": [155.0, 156.0, 157.0],
        "Low": [148.0, 149.0, 150.0],
        "Close": [153.0, 154.0, 155.0],
        "Volume": [1000000, 1100000, 1200000],
    }

    mock_news = [
        {
            "title": "Test News Article",
            "link": "https://example.com/news",
            "publisher": "Test Publisher",
            "providerPublishTime": 1700000000,
            "type": "STORY",
        }
    ]

    class MockTicker:
        """Mock yfinance Ticker class"""

        def __init__(self, symbol):
            self.symbol = symbol
            self._info = mock_info.copy()
            self._news = mock_news.copy()

        @property
        def info(self):
            return self._info

        @property
        def news(self):
            return self._news

        def history(self, period=None, interval=None):
            # Note: pandas import is done at module level in conftest.py,
            # but since we're in a MockTicker class, we import locally
            # to avoid polluting the module namespace
            import pandas as pd

            index = pd.date_range(start="2024-01-01", periods=3, freq="D")
            return pd.DataFrame(mock_history_data, index=index)

    patches = []

    # Patch yfinance.Ticker at multiple locations to ensure coverage
    # Patch the main yfinance module
    p1 = patch("yfinance.Ticker", MockTicker)
    p1.start()
    patches.append(p1)

    # Also patch at the provider level to handle cases where yfinance is
    # already imported
    with contextlib.suppress(AttributeError, ImportError, ModuleNotFoundError):
        p2 = patch("fiml.providers.yahoo_finance.yf.Ticker", MockTicker)
        p2.start()
        patches.append(p2)

    yield

    # Stop all patches
    for p in patches:
        with contextlib.suppress(Exception):
            p.stop()


@pytest.fixture(autouse=True)
def mock_ccxt_network_calls(request):
    """
    Mock CCXT network calls to prevent tests from making real HTTP requests
    to cryptocurrency exchanges like Binance.

    This fixture is autouse=True, so it applies to all tests automatically.
    Tests that need real API calls should use the @pytest.mark.live marker.
    """
    # Skip mocking for live tests
    if "live" in request.keywords:
        yield
        return

    # Create a factory function that creates mock exchange instances
    def create_mock_exchange():
        mock_exchange = AsyncMock()
        mock_exchange.load_markets = AsyncMock(return_value=None)
        mock_exchange.markets = {
            "BTC/USDT": {"symbol": "BTC/USDT", "base": "BTC", "quote": "USDT"},
            "ETH/USDT": {"symbol": "ETH/USDT", "base": "ETH", "quote": "USDT"},
        }
        mock_exchange.fetch_ticker = AsyncMock(
            return_value={
                "last": 43250.50,
                "bid": 43248.00,
                "ask": 43252.00,
                "high": 44000.00,
                "low": 42500.00,
                "open": 43000.00,
                "close": 43250.50,
                "baseVolume": 15000.5,
                "quoteVolume": 650000000,
                "change": 250.50,
                "percentage": 0.58,
                "timestamp": 1705334400000,
                "datetime": "2024-01-15T12:00:00.000Z",
            }
        )
        mock_exchange.fetch_status = AsyncMock(return_value={"status": "ok"})
        mock_exchange.close = AsyncMock()
        return mock_exchange

    # Create a mock class that returns mock exchange instances
    class MockExchangeClass:
        def __init__(self, *args, **kwargs):
            self._mock = create_mock_exchange()

        def __getattr__(self, name):
            return getattr(self._mock, name)

    # Patch at multiple levels to ensure coverage
    patches = []
    exchanges_to_patch = [
        "binance",
        "coinbase",
        "kraken",
        "bybit",
        "okx",
        "huobi",
        "kucoin",
        "gateio",
        "bitget",  # Additional public API exchanges
    ]

    # Patch ccxt.async_support module to return mock classes
    for exchange_name in exchanges_to_patch:
        with contextlib.suppress(AttributeError, ImportError, ModuleNotFoundError):
            # Patch in ccxt.async_support
            p = patch(f"ccxt.async_support.{exchange_name}", MockExchangeClass)
            p.start()
            patches.append(p)
            # Also patch direct ccxt module
            p2 = patch(f"ccxt.{exchange_name}", MockExchangeClass)
            p2.start()
            patches.append(p2)

    # Most importantly - patch the ccxt module reference used in ccxt_provider.py
    # This is the key fix: patch 'fiml.providers.ccxt_provider.ccxt' which is where
    # the module is actually accessed in the provider code
    try:
        import ccxt.async_support as ccxt_module

        # Create a mock module that returns our mock class for any exchange
        class MockCCXTModule:
            def __getattr__(self, name):
                if name in exchanges_to_patch:
                    return MockExchangeClass
                return getattr(ccxt_module, name)

        p = patch("fiml.providers.ccxt_provider.ccxt", MockCCXTModule())
        p.start()
        patches.append(p)
    except (AttributeError, ImportError, ModuleNotFoundError):
        # ccxt not installed - skip this patch
        pass

    yield

    # Stop all patches
    for p in patches:
        with contextlib.suppress(Exception):
            p.stop()


@pytest.fixture(autouse=True)
def mock_aiohttp_for_providers(request):
    """
    Mock aiohttp.ClientSession.get for provider API calls to external services.

    This prevents tests from making real HTTP requests to third-party APIs
    like CoinGecko, NewsAPI, Polygon, Finnhub, etc.

    Note: This only mocks specific financial data API domains, not all HTTP calls.
    Tests that need real API calls should use the @pytest.mark.live marker.
    """
    # Skip mocking for live tests
    if "live" in request.keywords:
        yield
        return
    # List of domains to mock (financial data providers and their dependencies)
    provider_domains = [
        # Financial data providers
        "api.coingecko.com",
        "pro-api.coinmarketcap.com",
        "api.polygon.io",
        "finnhub.io",
        "api.twelvedata.com",
        "api.tiingo.com",
        "api.intrinio.com",
        "api.marketstack.com",
        "www.quandl.com",
        "data.nasdaq.com",
        "newsapi.org",
        "www.alphavantage.co",
        "financialmodelingprep.com",
        # DefiLlama domains
        "coins.llama.fi",
        "api.llama.fi",
        # Yahoo Finance domains
        "fc.yahoo.com",
        "guce.yahoo.com",
        "query1.finance.yahoo.com",
        "query2.finance.yahoo.com",
        "finance.yahoo.com",
        # Cryptocurrency exchanges
        "api.binance.com",
        "api.coinbase.com",
        "api.kraken.com",
        "api.bybit.com",
        "api.huobi.pro",
        "www.okx.com",
        # Additional CCXT exchanges
        "api.kucoin.com",
        "api.gateio.ws",
        "api.bitget.com",
    ]

    # Create a mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"status": "ok", "data": {}})
    mock_response.text = AsyncMock(return_value='{"status": "ok"}')
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    original_get = None

    def selective_mock_get(self, url, *args, **kwargs):
        """Only mock calls to financial data provider domains"""
        url_str = str(url)

        # Check if this is a call to a provider domain
        for domain in provider_domains:
            if domain in url_str:
                return mock_response

        # For all other calls, use the original method
        if original_get is not None:
            return original_get(self, url, *args, **kwargs)

        # Fallback: return mock response to be safe
        return mock_response

    import aiohttp

    original_get = aiohttp.ClientSession.get

    with patch.object(aiohttp.ClientSession, "get", selective_mock_get):
        yield


@pytest.fixture(scope="function", autouse=True)
def configure_caplog(caplog):
    """
    Configure caplog to capture all log levels for each test.

    This ensures caplog.text contains all logged messages during test execution.
    The 'function' scope ensures each test gets a fresh caplog instance.
    """
    import logging

    caplog.set_level(logging.DEBUG)
    yield
