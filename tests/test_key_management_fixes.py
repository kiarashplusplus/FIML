from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Mock the lifespan to avoid starting heavy services
@asynccontextmanager
async def mock_lifespan(app):
    yield

with patch("fiml.server.lifespan", mock_lifespan):
    from fiml.server import app
    from fiml.services.user_key_onboarding_service import UserKeyOnboardingService

# Mock storage for the service
class MockStorage:
    def __init__(self):
        self.keys = {}

    async def list_all(self, user_id):
        return list(self.keys.get(user_id, {}).keys())

    async def retrieve(self, user_id, provider):
        return self.keys.get(user_id, {}).get(provider)

    async def store(self, user_id, provider, encrypted_key, metadata):
        if user_id not in self.keys:
            self.keys[user_id] = {}
        self.keys[user_id][provider] = {
            "encrypted_key": encrypted_key,
            "metadata": metadata or {},
            "added_at": "2024-01-01T00:00:00Z"
        }
        return True

    async def get_all_keys(self, user_id):
        return self.keys.get(user_id, {})

@pytest.fixture(scope="session", autouse=True)
def docker_services():
    """Override docker_services to do nothing"""
    yield

@pytest.fixture(autouse=True)
def reset_provider_registry():
    """Override reset_provider_registry to do nothing"""
    yield

@pytest.fixture
def mock_service():
    # Mock UserProviderKeyManager interface
    service = MagicMock()

    # Use real PROVIDER_INFO from the class to verify we have all of them
    real_providers = [{"id": k, **v} for k, v in UserKeyOnboardingService.PROVIDER_INFO.items()]
    service.list_supported_providers.return_value = real_providers

    # Mock list_user_keys (async)
    service.list_user_keys = AsyncMock(return_value=[])

    # Mock get_provider_info
    service.get_provider_info.side_effect = lambda p: UserKeyOnboardingService.PROVIDER_INFO.get(p)

    # Mock validate_key_format
    service.validate_key_format.return_value = True

    # Mock add_key (async)
    service.add_key = AsyncMock(return_value={"success": True})

    # Mock _service.KEY_PATTERNS for the validate-format endpoint
    mock_inner_service = MagicMock()
    mock_inner_service.KEY_PATTERNS = UserKeyOnboardingService.KEY_PATTERNS
    service._service = mock_inner_service

    return service

@pytest.fixture
def client(mock_service):
    # Override the get_key_service dependency
    with (
        patch("fiml.bot.key_router.get_key_service", return_value=mock_service),
        TestClient(app) as c,
    ):
        yield c

def test_get_provider_status_returns_all_providers(client):
    response = client.get("/api/user/test_user/keys")
    assert response.status_code == 200
    data = response.json()

    providers = data["providers"]
    # We expect 17 providers now
    assert len(providers) >= 17

    # Check for specific providers that were missing
    provider_names = [p["name"] for p in providers]
    assert "ccxt-kraken" in provider_names
    assert "coingecko" in provider_names
    assert "alpha_vantage" in provider_names
    assert "fmp" in provider_names

def test_validate_key_format_for_new_provider(client):
    # Test validation for a provider that was previously unknown
    response = client.post(
        "/api/user/test_user/keys/ccxt-kraken/validate-format",
        json={"api_key": "some_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["provider"] == "ccxt-kraken"

def test_add_key_for_supported_provider(client):
    response = client.post(
        "/api/user/test_user/keys",
        json={"provider": "alpha_vantage", "api_key": "TEST_KEY_123"}
    )
    assert response.status_code == 201
    assert response.json()["success"] is True
