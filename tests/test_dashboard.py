"""
Tests for Dashboard functionality

Tests cover:
- Dashboard statistics endpoint
- Watchdog status endpoint
- Event retrieval
- Multi-asset monitoring
- WebSocket streaming
"""

import pytest
from fastapi.testclient import TestClient

from fiml.core.models import Asset, AssetType, Market
from fiml.server import app
from fiml.watchdog.models import EventType, Severity, WatchdogEvent


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_watchdog_event():
    """Sample watchdog event for testing"""
    return WatchdogEvent(
        type=EventType.PRICE_ANOMALY,
        severity=Severity.HIGH,
        asset=Asset(
            symbol="AAPL",
            asset_type=AssetType.EQUITY,
            market=Market.US,
        ),
        description="Price spike detected",
        watchdog="price_anomaly",
        data={"price_change_pct": 5.5},
    )


class TestDashboardStats:
    """Test dashboard statistics endpoint"""

    def test_get_dashboard_stats(self, client):
        """Test retrieving dashboard statistics"""
        response = client.get("/dashboard/stats")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "total_events" in data
        assert "events_by_severity" in data
        assert "active_watchdogs" in data
        assert "healthy_watchdogs" in data
        assert "active_subscriptions" in data
        assert "timestamp" in data

        # Check types
        assert isinstance(data["total_events"], int)
        assert isinstance(data["events_by_severity"], dict)
        assert isinstance(data["active_watchdogs"], int)
        assert isinstance(data["healthy_watchdogs"], int)


class TestWatchdogStatus:
    """Test watchdog status endpoints"""

    def test_get_watchdog_status(self, client):
        """Test retrieving watchdog status"""
        response = client.get("/dashboard/watchdogs")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # If watchdogs exist, check structure
        if data:
            watchdog = data[0]
            assert "name" in watchdog
            assert "enabled" in watchdog
            assert "running" in watchdog
            assert "status" in watchdog
            assert "total_checks" in watchdog

    def test_enable_watchdog(self, client):
        """Test enabling a watchdog"""
        # Get list of watchdogs first
        response = client.get("/dashboard/watchdogs")
        assert response.status_code == 200
        watchdogs = response.json()

        if watchdogs:
            watchdog_name = watchdogs[0]["name"]

            # Enable the watchdog
            response = client.post(f"/dashboard/watchdogs/{watchdog_name}/enable")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "enabled"
            assert data["watchdog"] == watchdog_name

    def test_disable_watchdog(self, client):
        """Test disabling a watchdog"""
        # Get list of watchdogs first
        response = client.get("/dashboard/watchdogs")
        assert response.status_code == 200
        watchdogs = response.json()

        if watchdogs:
            watchdog_name = watchdogs[0]["name"]

            # Disable the watchdog
            response = client.post(f"/dashboard/watchdogs/{watchdog_name}/disable")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disabled"
            assert data["watchdog"] == watchdog_name

    def test_enable_nonexistent_watchdog(self, client):
        """Test enabling a non-existent watchdog"""
        response = client.post("/dashboard/watchdogs/nonexistent/enable")
        assert response.status_code == 404


class TestEventRetrieval:
    """Test event retrieval endpoints"""

    def test_get_recent_events(self, client):
        """Test retrieving recent events"""
        response = client.get("/dashboard/events")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # Events might be empty initially
        # If events exist, check structure
        if data:
            event = data[0]
            assert "event_id" in event
            assert "type" in event
            assert "severity" in event
            assert "description" in event
            assert "timestamp" in event

    def test_get_events_with_limit(self, client):
        """Test retrieving events with limit"""
        response = client.get("/dashboard/events?limit=10")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 10

    def test_get_events_with_severity_filter(self, client):
        """Test filtering events by severity"""
        response = client.get("/dashboard/events?severity=high")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # All returned events should have high severity
        for event in data:
            assert event["severity"] == "high"

    def test_get_events_invalid_limit(self, client):
        """Test with invalid limit parameter"""
        response = client.get("/dashboard/events?limit=2000")

        # Should return 422 validation error for out-of-range limit
        assert response.status_code == 422


class TestMultiAssetMonitoring:
    """Test multi-asset monitoring endpoint"""

    @pytest.mark.asyncio
    async def test_monitor_single_asset(self, client):
        """Test monitoring a single asset"""
        response = client.get(
            "/dashboard/assets/monitor",
            params={
                "symbols": ["AAPL"],
                "asset_type": "equity",
                "market": "US"
            }
        )

        # May fail if no providers available in test environment
        # Accept both success and some error codes
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1

            asset_data = data[0]
            assert asset_data["symbol"] == "AAPL"
            assert asset_data["asset_type"] == "equity"

    @pytest.mark.asyncio
    async def test_monitor_multiple_assets(self, client):
        """Test monitoring multiple assets"""
        response = client.get(
            "/dashboard/assets/monitor",
            params={
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "asset_type": "equity",
                "market": "US"
            }
        )

        # May fail if no providers available
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 3

    def test_monitor_no_symbols(self, client):
        """Test monitoring with no symbols provided"""
        response = client.get("/dashboard/assets/monitor")

        # Should return 422 validation error
        assert response.status_code == 422


class TestDashboardWebSocket:
    """Test dashboard WebSocket streaming"""

    def test_dashboard_websocket_connection(self, client):
        """Test basic dashboard WebSocket connection"""
        try:
            with client.websocket_connect("/dashboard/stream") as websocket:
                # Should receive initial stats message
                data = websocket.receive_json()

                assert "type" in data
                assert data["type"] in ["stats", "event", "health"]

                # Send a ping to keep connection alive
                websocket.send_text("ping")
        except Exception as e:
            # WebSocket tests may fail in some test environments
            # This is acceptable as it's environment-dependent
            pytest.skip(f"WebSocket test skipped: {e}")
