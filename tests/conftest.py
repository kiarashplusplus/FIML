"""
Test configuration for FIML
"""

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
    if hasattr(config_module, 'get_settings'):
        config_module.get_settings.cache_clear()
        # Reload global settings
        config_module.settings = config_module.get_settings()


def pytest_addoption(parser):
    """Add custom command-line options"""
    parser.addoption(
        "--run-cache-tests",
        action="store_true",
        default=False,
        help="Run tests that require Redis/PostgreSQL cache backends"
    )
    parser.addoption(
        "--no-docker",
        action="store_true",
        default=False,
        help="Skip Docker container startup (assume services are already running)"
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
                connect_timeout=1
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
            pytest.exit("PostgreSQL is not available. Please start PostgreSQL or remove --no-docker flag.")
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
        ["docker", "compose", "-f", compose_file, "up", "-d"],
        cwd=project_root,
        check=True,
        capture_output=True
    )

    # Wait for services to be ready
    print("⏳ Waiting for Redis to be ready...")
    if not is_redis_ready():
        subprocess.run(["docker", "compose", "-f", compose_file, "down", "-v"], cwd=project_root)
        pytest.exit("Redis failed to start within timeout period")
    print("✅ Redis is ready")

    print("⏳ Waiting for PostgreSQL to be ready...")
    if not is_postgres_ready():
        subprocess.run(["docker", "compose", "-f", compose_file, "down", "-v"], cwd=project_root)
        pytest.exit("PostgreSQL failed to start within timeout period")
    print("✅ PostgreSQL is ready")

    print("✅ All test services are ready\n")

    yield

    # Teardown: stop and remove containers
    print("\n🧹 Cleaning up test containers...")
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "down", "-v"],
        cwd=project_root,
        capture_output=True
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
    # Only mock if we're using the mock endpoint
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    if azure_endpoint.startswith("https://mock"):
        # Create a mock response that mimics Azure OpenAI's response format
        mock_openai_response = MagicMock()
        mock_openai_response.status_code = 200
        mock_openai_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a mock response from Azure OpenAI for testing purposes.",
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
            # Check if this is an Azure OpenAI call
            if "openai.azure.com" in url_str or "mock-azure-openai" in url_str:
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
    else:
        # If using real endpoint, don't mock anything
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
            statements = CREATE_TABLES_SQL.strip().split(';')
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
    # If _redis is now a MagicMock or was set to something different (but not a real redis connection)
    # while _initialized is True, reset everything
    if l1_cache._initialized and l1_cache._redis is not initial_l1_redis:
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

