"""
Tests for API Key Management Router (key_router.py)
Covers: GET, POST, DELETE, and format validation endpoints
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fiml.bot.key_router import (
    AddKeyRequest,
    KeyResponse,
    Provider,
    ValidateKeyRequest,
    router,
)


@pytest.fixture
def mock_key_service():
    """Mock UserProviderKeyManager for testing"""
    service = AsyncMock()
    service.list_keys = AsyncMock(return_value=["binance", "alphavantage"])
    service.get_provider_info = MagicMock(return_value={"name": "binance", "displayName": "Binance"})
    service.get_key = AsyncMock(return_value="test_api_key_123")
    service.add_key = AsyncMock()
    service.remove_key = AsyncMock()
    service.test_provider_key = AsyncMock(return_value={"valid": True, "message": "Key is valid", "tier": "premium"})
    service.validate_key_format = MagicMock(return_value=True)
    service._service = MagicMock()
    service._service.KEY_PATTERNS = {
        "binance": "64 character hexadecimal",
        "alphavantage": "16 uppercase alphanumeric"
    }
    return service


@pytest.fixture
def client():
    """TestClient for FastAPI router"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestGetProviderStatus:
    """Tests for GET /api/user/{user_id}/keys"""

    @patch('fiml.bot.key_router.get_key_service')
    async def test_get_provider_status_success(self, mock_get_service, client, mock_key_service):
        """Test successful retrieval of provider status"""
        mock_get_service.return_value = mock_key_service

        response = client.get("/api/user/user123/keys")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) > 0

        # Check that binance and alphavantage are connected
        provider_names = {p["name"]: p["isConnected"] for p in data["providers"]}
        assert provider_names.get("binance") is True
        assert provider_names.get("alphavantage") is True
        assert provider_names.get("coinbase") is False

    @patch('fiml.bot.key_router.get_key_service')
    async def test_get_provider_status_error_fallback(self, mock_get_service, client):
        """Test  fallback to default providers on error"""
        mock_service = AsyncMock()
        mock_service.list_keys = AsyncMock(side_effect=Exception("Database error"))
        mock_get_service.return_value = mock_service

        response = client.get("/api/user/user123/keys")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        # Should return default providers with isConnected=False
        assert all(not p["isConnected"] for p in data["providers"])


class TestValidateKeyFormat:
    """Tests for POST /api/user/{user_id}/keys/{provider}/validate-format"""

    @patch('fiml.bot.key_router.get_key_service')
    async def test_validate_format_valid_key(self, mock_get_service, client, mock_key_service):
        """Test validation of valid API key format"""
        mock_get_service.return_value = mock_key_service

        response = client.post(
            "/api/user/user123/keys/binance/validate-format",
            json={"api_key": "a1b2c3d4e5f6"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "message" in data

    @patch('fiml.bot.key_router.get_key_service')
    async def test_validate_format_invalid_key(self, mock_get_service, client, mock_key_service):
        """Test validation of invalid API key format"""
        mock_key_service.validate_key_format = MagicMock(return_value=False)
        mock_get_service.return_value = mock_key_service

        response = client.post(
            "/api/user/user123/keys/binance/validate-format",
            json={"api_key": "invalid"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "expected_pattern" in data

    @patch('fiml.bot.key_router.get_key_service')
    async def test_validate_format_unknown_provider(self, mock_get_service, client, mock_key_service):
        """Test validation with unknown provider"""
        mock_key_service.get_provider_info = MagicMock(return_value=None)
        mock_get_service.return_value = mock_key_service

        response = client.post(
            "/api/user/user123/keys/unknown_provider/validate-format",
            json={"api_key": "test123"}
        )

        assert response.status_code == 400
        assert "Unknown provider" in response.json()["detail"]


class TestAddKey:
    """Tests for POST /api/user/{user_id}/keys"""

    @patch('fiml.bot.key_router.get_key_service')
    async def test_add_key_success(self, mock_get_service, client, mock_key_service):
        """Test successful API key addition"""
        mock_get_service.return_value = mock_key_service

        response = client.post(
            "/api/user/user123/keys",
            json={
                "provider": "binance",
                "api_key": "test_api_key_123",
                "api_secret": "test_secret_456"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "Binance" in data["message"]

        # Verify service was called correctly
        mock_key_service.add_key.assert_called_once()

    @patch('fiml.bot.key_router.get_key_service')
    async def test_add_key_unknown_provider(self, mock_get_service, client, mock_key_service):
        """Test adding key with unknown provider"""
        mock_key_service.get_provider_info = MagicMock(return_value=None)
        mock_get_service.return_value = mock_key_service

        response = client.post(
            "/api/user/user123/keys",
            json={
                "provider": "invalid_provider",
                "api_key": "test_key"
            }
        )

        assert response.status_code == 400
        assert "Unknown provider" in response.json()["detail"]

    @patch('fiml.bot.key_router.get_key_service')
    async def test_add_key_service_error(self, mock_get_service, client, mock_key_service):
        """Test add key with service error"""
        mock_key_service.add_key = AsyncMock(side_effect=Exception("Database error"))
        mock_get_service.return_value = mock_key_service

        response = client.post(
            "/api/user/user123/keys",
            json={
                "provider": "binance",
                "api_key": "test_key"
            }
        )

        assert response.status_code == 500
        assert "Failed to add API key" in response.json()["detail"]


class TestTestKey:
    """Tests for POST /api/user/{user_id}/keys/{provider}/test"""

    @patch('fiml.bot.key_router.get_key_service')
    async def test_test_key_valid(self, mock_get_service, client, mock_key_service):
        """Test testing a valid API key"""
        mock_get_service.return_value = mock_key_service

        response = client.post("/api/user/user123/keys/binance/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Key is valid" in data["message"]

    @patch('fiml.bot.key_router.get_key_service')
    async def test_test_key_not_found(self, mock_get_service, client, mock_key_service):
        """Test testing with no key configured"""
        mock_key_service.get_key = AsyncMock(return_value=None)
        mock_get_service.return_value = mock_key_service

        response = client.post("/api/user/user123/keys/binance/test")

        assert response.status_code == 404
        assert "No API key found" in response.json()["detail"]

    @patch('fiml.bot.key_router.get_key_service')
    async def test_test_key_validation_failed(self, mock_get_service, client, mock_key_service):
        """Test testing with invalid key"""
        mock_key_service.test_provider_key = AsyncMock(return_value={
            "valid": False,
            "message": "Invalid API key"
        })
        mock_get_service.return_value = mock_key_service

        response = client.post("/api/user/user123/keys/binance/test")

        assert response.status_code == 400
        assert "Key validation failed" in response.json()["detail"]

    @patch('fiml.bot.key_router.get_key_service')
    async def test_test_key_service_error(self, mock_get_service, client, mock_key_service):
        """Test test key with service error"""
        mock_key_service.test_provider_key = AsyncMock(side_effect=Exception("Network error"))
        mock_get_service.return_value = mock_key_service

        response = client.post("/api/user/user123/keys/binance/test")

        assert response.status_code == 500
        assert "Failed to test API key" in response.json()["detail"]


class TestRemoveKey:
    """Tests for DELETE /api/user/{user_id}/keys/{provider}"""

    @patch('fiml.bot.key_router.get_key_service')
    async def test_remove_key_success(self, mock_get_service, client, mock_key_service):
        """Test successful key removal"""
        mock_get_service.return_value = mock_key_service

        response = client.delete("/api/user/user123/keys/binance")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "removed successfully" in data["message"]

        # Verify service was called
        mock_key_service.remove_key.assert_called_once_with("user123", "binance")

    @patch('fiml.bot.key_router.get_key_service')
    async def test_remove_key_not_found(self, mock_get_service, client, mock_key_service):
        """Test removing non-existent key"""
        mock_key_service.get_key = AsyncMock(return_value=None)
        mock_get_service.return_value = mock_key_service

        response = client.delete("/api/user/user123/keys/binance")

        assert response.status_code == 404
        assert "No API key found" in response.json()["detail"]

    @patch('fiml.bot.key_router.get_key_service')
    async def test_remove_key_service_error(self, mock_get_service, client, mock_key_service):
        """Test remove key with service error"""
        mock_key_service.remove_key = AsyncMock(side_effect=Exception("Database error"))
        mock_get_service.return_value = mock_key_service

        response = client.delete("/api/user/user123/keys/binance")

        assert response.status_code == 500
        assert "Failed to remove API key" in response.json()["detail"]


class TestPydanticModels:
    """Test Pydantic model validation"""

    def test_provider_model(self):
        """Test Provider model validation"""
        provider = Provider(
            name="binance",
            displayName="Binance",
            isConnected=True,
            description="Crypto exchange"
        )
        assert provider.name == "binance"
        assert provider.isConnected is True

    def test_add_key_request_model(self):
        """Test AddKeyRequest model"""
        request = AddKeyRequest(
            provider="binance",
            api_key="test123",
            api_secret="secret456"
        )
        assert request.provider == "binance"
        assert request.api_secret == "secret456"

    def test_add_key_request_without_secret(self):
        """Test AddKeyRequest without secret"""
        request = AddKeyRequest(
            provider="alphavantage",
            api_key="test123"
        )
        assert request.api_secret is None

    def test_validate_key_request_model(self):
        """Test ValidateKeyRequest model"""
        request = ValidateKeyRequest(api_key="test123")
        assert request.api_key == "test123"

    def test_key_response_model(self):
        """Test KeyResponse model"""
        response = KeyResponse(
            success=True,
            message="Success"
        )
        assert response.success is True
        assert response.error is None
