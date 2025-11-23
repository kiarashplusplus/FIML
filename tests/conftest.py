"""
Test configuration for FIML
"""

import os
import subprocess
import time

import psycopg2
import pytest
import redis
from dotenv import load_dotenv

# Load .env file first to get real configuration
load_dotenv()

from fiml.core.config import Settings

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
        ["docker-compose", "-f", compose_file, "up", "-d"],
        cwd=project_root,
        check=True,
        capture_output=True
    )

    # Wait for services to be ready
    print("⏳ Waiting for Redis to be ready...")
    if not is_redis_ready():
        subprocess.run(["docker-compose", "-f", compose_file, "down", "-v"], cwd=project_root)
        pytest.exit("Redis failed to start within timeout period")
    print("✅ Redis is ready")

    print("⏳ Waiting for PostgreSQL to be ready...")
    if not is_postgres_ready():
        subprocess.run(["docker-compose", "-f", compose_file, "down", "-v"], cwd=project_root)
        pytest.exit("PostgreSQL failed to start within timeout period")
    print("✅ PostgreSQL is ready")

    print("✅ All test services are ready\n")

    yield

    # Teardown: stop and remove containers
    print("\n🧹 Cleaning up test containers...")
    subprocess.run(
        ["docker-compose", "-f", compose_file, "down", "-v"],
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


