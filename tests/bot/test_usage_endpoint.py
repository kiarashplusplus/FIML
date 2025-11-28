"""
Integration tests for Usage Statistics API endpoint

Tests the GET /api/user/{user_id}/usage endpoint with:
- Full request/response cycle
- Query parameter filtering
- Pydantic model validation
- Error handling
- Authentication headers
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from fiml.bot.key_router import router, get_key_service
from fiml.bot.core.key_manager import UserProviderKeyManager


@pytest.fixture
def mock_key_manager():
    """Mock UserProviderKeyManager with usage analytics"""
    manager = MagicMock(spec=UserProviderKeyManager)
    
    # Mock usage_analytics
    manager.usage_analytics = MagicMock()
    manager.usage_analytics.get_usage = AsyncMock()
    manager.usage_analytics.check_quota = AsyncMock()
    manager.usage_analytics.get_provider_limits = MagicMock()
    
    # Mock get_all_usage_stats
    manager.get_all_usage_stats = AsyncMock()
    
    return manager


@pytest.fixture
def client(mock_key_manager):
    """FastAPI test client with mocked dependencies"""
    from fastapi import FastAPI
    
    # Patch get_key_service to return our mock
    with patch('fiml.bot.key_router.get_key_service', return_value=mock_key_manager):
        app = FastAPI()
        app.include_router(router)
        
        yield TestClient(app)


class TestUsageStatsEndpoint:
    """Test GET /api/user/{user_id}/usage endpoint"""

    def test_get_all_usage_stats_success(self, client, mock_key_manager):
        """Test getting usage stats for all providers"""
        # Mock response data
        mock_key_manager.get_all_usage_stats.return_value = {
            "stats": [
                {
                    "provider": "binance",
                    "daily_usage": 45,
                    "daily_limit": 1200,
                    "monthly_usage": 320,
                    "monthly_limit": 36000,
                    "daily_percentage": 3.75,
                    "monthly_percentage": 0.89,
                    "warning": False,
                    "tier": "free"
                },
                {
                    "provider": "alphavantage",
                    "daily_usage": 420,
                    "daily_limit": 500,
                    "monthly_usage": 12000,
                    "monthly_limit": 25000,
                    "daily_percentage": 84.0,
                    "monthly_percentage": 48.0,
                    "warning": True,
                    "tier": "free"
                }
            ],
            "total_calls_today": 465,
            "has_warnings": True,
            "timestamp": "2025-11-28T14:00:00Z"
        }
        
        # Make request
        response = client.get(
            "/api/user/test_user/usage",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["stats"]) == 2
        assert data["total_calls_today"] == 465
        assert data["has_warnings"] is True
        assert "timestamp" in data
        
        # Verify first provider
        binance = data["stats"][0]
        assert binance["provider"] == "binance"
        assert binance["daily_usage"] == 45
        assert binance["daily_limit"] == 1200
        assert binance["warning"] is False
        
        # Verify second provider (warning)
        alphavantage = data["stats"][1]
        assert alphavantage["provider"] == "alphavantage"
        assert alphavantage["daily_percentage"] == 84.0
        assert alphavantage["warning"] is True

    def test_get_single_provider_usage(self, client, mock_key_manager):
        """Test getting usage stats for single provider"""
        # Mock individual provider data
        mock_key_manager.usage_analytics.get_usage.side_effect = [45, 320]  # daily, monthly
        mock_key_manager.usage_analytics.check_quota.return_value = {
            "daily_usage": 45,
            "daily_limit": 1200,
            "monthly_usage": 320,
            "monthly_limit": 36000,
            "daily_percentage": 3.75,
            "monthly_percentage": 0.89,
            "warning": False,
            "exceeded": False
        }
        mock_key_manager.usage_analytics.get_provider_limits.return_value = {
            "tier": "free"
        }
        
        # Make request with provider filter
        response = client.get(
            "/api/user/test_user/usage?provider=binance",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["stats"]) == 1
        assert data["stats"][0]["provider"] == "binance"
        assert data["total_calls_today"] == 45
        assert data["has_warnings"] is False
        
        # Verify service calls
        mock_key_manager.usage_analytics.get_usage.assert_any_call("test_user", "binance", "daily")
        mock_key_manager.usage_analytics.get_usage.assert_any_call("test_user", "binance", "monthly")
        mock_key_manager.usage_analytics.check_quota.assert_called_once_with("test_user", "binance")

    def test_get_usage_no_data(self, client, mock_key_manager):
        """Test getting usage when no providers have been used"""
        mock_key_manager.get_all_usage_stats.return_value = {
            "stats": [],
            "total_calls_today": 0,
            "has_warnings": False,
            "timestamp": "2025-11-28T14:00:00Z"
        }
        
        response = client.get(
            "/api/user/test_user/usage",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["stats"] == []
        assert data["total_calls_today"] == 0
        assert data["has_warnings"] is False

    def test_get_usage_with_warnings(self, client, mock_key_manager):
        """Test response when providers have quota warnings"""
        mock_key_manager.get_all_usage_stats.return_value = {
            "stats": [
                {
                    "provider": "alphavantage",
                    "daily_usage": 450,
                    "daily_limit": 500,
                    "monthly_usage": 12000,
                    "monthly_limit": 25000,
                    "daily_percentage": 90.0,
                    "monthly_percentage": 48.0,
                    "warning": True,
                    "tier": "free"
                }
            ],
            "total_calls_today": 450,
            "has_warnings": True,
            "timestamp": "2025-11-28T14:00:00Z"
        }
        
        response = client.get("/api/user/test_user/usage")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_warnings"] is True
        assert data["stats"][0]["warning"] is True
        assert data["stats"][0]["daily_percentage"] == 90.0

    def test_get_usage_exceeded_quota(self, client, mock_key_manager):
        """Test response when quota is exceeded"""
        mock_key_manager.usage_analytics.get_usage.side_effect = [1250, 320]
        mock_key_manager.usage_analytics.check_quota.return_value = {
            "daily_usage": 1250,
            "daily_limit": 1200,
            "monthly_usage": 320,
            "monthly_limit": 36000,
            "daily_percentage": 104.17,
            "monthly_percentage": 0.89,
            "warning": True,
            "exceeded": True
        }
        mock_key_manager.usage_analytics.get_provider_limits.return_value = {"tier": "free"}
        
        response = client.get("/api/user/test_user/usage?provider=binance")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["stats"][0]["daily_usage"] > data["stats"][0]["daily_limit"]
        assert data["stats"][0]["warning"] is True

    def test_get_usage_service_error(self, client, mock_key_manager):
        """Test error handling when service fails"""
        mock_key_manager.get_all_usage_stats.side_effect = Exception("Database error")
        
        response = client.get("/api/user/test_user/usage")
        
        assert response.status_code == 500
        assert "Failed to fetch usage statistics" in response.json()["detail"]

    def test_get_usage_pydantic_validation(self, client, mock_key_manager):
        """Test that response validates against Pydantic models"""
        mock_key_manager.get_all_usage_stats.return_value = {
            "stats": [
                {
                    "provider": "binance",
                    "daily_usage": 45,
                    "daily_limit": 1200,
                    "monthly_usage": 320,
                    "monthly_limit": 36000,
                    "daily_percentage": 3.75,
                    "monthly_percentage": 0.89,
                    "warning": False,
                    "tier": "free"
                }
            ],
            "total_calls_today": 45,
            "has_warnings": False,
            "timestamp": "2025-11-28T14:00:00Z"
        }
        
        response = client.get("/api/user/test_user/usage")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields present
        assert "stats" in data
        assert "total_calls_today" in data
        assert "has_warnings" in data
        assert "timestamp" in data
        
        # Verify stats structure
        stat = data["stats"][0]
        required_fields = [
            "provider", "daily_usage", "daily_limit", "monthly_usage",
            "monthly_limit", "daily_percentage", "monthly_percentage",
            "warning", "tier"
        ]
        for field in required_fields:
            assert field in stat

    def test_get_usage_multiple_providers_sorted(self, client, mock_key_manager):
        """Test that providers are sorted by daily usage"""
        mock_key_manager.get_all_usage_stats.return_value = {
            "stats": [
                {
                    "provider": "alphavantage",
                    "daily_usage": 420,
                    "daily_limit": 500,
                    "monthly_usage": 12000,
                    "monthly_limit": 25000,
                    "daily_percentage": 84.0,
                    "monthly_percentage": 48.0,
                    "warning": True,
                    "tier": "free"
                },
                {
                    "provider": "binance",
                    "daily_usage": 45,
                    "daily_limit": 1200,
                    "monthly_usage": 320,
                    "monthly_limit": 36000,
                    "daily_percentage": 3.75,
                    "monthly_percentage": 0.89,
                    "warning": False,
                    "tier": "free"
                }
            ],
            "total_calls_today": 465,
            "has_warnings": True,
            "timestamp": "2025-11-28T14:00:00Z"
        }
        
        response = client.get("/api/user/test_user/usage")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify sorting (highest usage first)
        assert data["stats"][0]["daily_usage"] >= data["stats"][1]["daily_usage"]
        assert data["stats"][0]["provider"] == "alphavantage"

    def test_get_usage_unlimited_provider(self, client, mock_key_manager):
        """Test handling of unlimited quota providers (yfinance)"""
        mock_key_manager.usage_analytics.get_usage.side_effect = [150, 4500]
        mock_key_manager.usage_analytics.check_quota.return_value = {
            "daily_usage": 150,
            "daily_limit": 999999999,  # Very large number instead of inf for JSON compatibility
            "monthly_usage": 4500,
            "monthly_limit": 999999999,
            "daily_percentage": 0.0,
            "monthly_percentage": 0.0,
            "warning": False,
            "exceeded": False
        }
        mock_key_manager.usage_analytics.get_provider_limits.return_value = {"tier": "free"}
        
        response = client.get("/api/user/test_user/usage?provider=yfinance")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify unlimited is represented correctly (as very large number)
        stat = data["stats"][0]
        assert stat["daily_usage"] == 150
        assert stat["daily_limit"] > 1000000  # Very large limit
        assert stat["warning"] is False  # Never warns for unlimited

    def test_get_usage_timestamp_format(self, client, mock_key_manager):
        """Test that timestamp is in ISO format"""
        mock_key_manager.get_all_usage_stats.return_value = {
            "stats": [],
            "total_calls_today": 0,
            "has_warnings": False,
            "timestamp": "2025-11-28T14:30:45.123456Z"
        }
        
        response = client.get("/api/user/test_user/usage")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify timestamp format
        timestamp = data["timestamp"]
        assert "T" in timestamp
        assert timestamp.endswith("Z") or "+" in timestamp  # UTC or timezone offset


class TestUsageStatsEndpointEdgeCases:
    """Test edge cases and error scenarios"""

    def test_invalid_user_id(self, client, mock_key_manager):
        """Test with empty user ID"""
        response = client.get("/api/user//usage")
        
        # Should return 404 (route not found) or 422 (validation error)
        assert response.status_code in [404, 422]

    def test_special_characters_in_provider(self, client, mock_key_manager):
        """Test provider name with special characters"""
        mock_key_manager.usage_analytics.get_usage.side_effect = [0, 0]
        mock_key_manager.usage_analytics.check_quota.return_value = {
            "daily_usage": 0,
            "daily_limit": 1000,
            "monthly_usage": 0,
            "monthly_limit": 30000,
            "daily_percentage": 0.0,
            "monthly_percentage": 0.0,
            "warning": False,
            "exceeded": False
        }
        mock_key_manager.usage_analytics.get_provider_limits.return_value = {"tier": "unknown"}
        
        response = client.get("/api/user/test_user/usage?provider=test-provider_123")
        
        # Should handle gracefully
        assert response.status_code == 200

    def test_very_large_usage_numbers(self, client, mock_key_manager):
        """Test with very large usage numbers"""
        mock_key_manager.get_all_usage_stats.return_value = {
            "stats": [
                {
                    "provider": "binance",
                    "daily_usage": 999999,
                    "daily_limit": 1200,
                    "monthly_usage": 29999999,
                    "monthly_limit": 36000,
                    "daily_percentage": 83333.25,
                    "monthly_percentage": 83333.33,
                    "warning": True,
                    "tier": "free"
                }
            ],
            "total_calls_today": 999999,
            "has_warnings": True,
            "timestamp": "2025-11-28T14:00:00Z"
        }
        
        response = client.get("/api/user/test_user/usage")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_calls_today"] == 999999
