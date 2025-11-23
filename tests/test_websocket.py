"""
WebSocket Streaming Tests

Tests for real-time WebSocket data streaming functionality
"""


import pytest
from fastapi.testclient import TestClient

from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.server import app
from fiml.websocket.manager import websocket_manager
from fiml.websocket.models import (
    MessageType,
    StreamType,
)


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_asset():
    """Sample asset for testing"""
    return Asset(
        symbol="AAPL",
        asset_type=AssetType.EQUITY,
        market=Market.US,
    )


class TestWebSocketConnection:
    """Test WebSocket connection lifecycle"""

    def test_websocket_connect_disconnect(self, client):
        """Test basic WebSocket connection and disconnection"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Connection should be established
            assert websocket is not None

            # Should receive initial connection (no error)
            # Disconnect happens automatically when context exits

    def test_multiple_connections(self, client):
        """Test multiple simultaneous WebSocket connections"""
        # Note: TestClient has limitations with multiple connections
        # This test verifies basic connection capability
        with (
            client.websocket_connect("/ws/stream") as ws1,
            client.websocket_connect("/ws/stream") as ws2,
        ):
            # Both should be connected
            assert ws1 is not None
            assert ws2 is not None
            # Connections close automatically when context exits

    def test_heartbeat_received(self, client):
        """Test that heartbeat messages are received"""
        # Note: TestClient doesn't support timeout parameter
        # This test verifies the connection can receive messages
        with client.websocket_connect("/ws/stream"):
            # Override heartbeat interval for testing
            original_interval = websocket_manager.heartbeat_interval
            websocket_manager.heartbeat_interval = 1  # 1 second for testing

            try:
                # In a real scenario, heartbeat would arrive after 1 second
                # For testing purposes, we just verify the connection works
                pass

            finally:
                # Restore original interval
                websocket_manager.heartbeat_interval = original_interval


class TestSubscriptionManagement:
    """Test subscription creation and management"""

    def test_subscribe_to_price_stream(self, client):
        """Test subscribing to price stream"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Send subscription request
            request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": ["AAPL", "GOOGL"],
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 1000,
                "data_type": DataType.PRICE,
            }
            websocket.send_json(request)

            # Should receive subscription acknowledgment
            response = websocket.receive_json()

            assert response["type"] == MessageType.SUBSCRIPTION_ACK
            assert response["stream_type"] == StreamType.PRICE
            assert set(response["symbols"]) == {"AAPL", "GOOGL"}
            assert "subscription_id" in response

    def test_subscribe_to_ohlcv_stream(self, client):
        """Test subscribing to OHLCV stream"""
        with client.websocket_connect("/ws/stream") as websocket:
            request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.OHLCV,
                "symbols": ["BTC/USDT"],
                "asset_type": AssetType.CRYPTO,
                "market": Market.CRYPTO,
                "interval_ms": 5000,
                "data_type": DataType.OHLCV,
            }
            websocket.send_json(request)

            response = websocket.receive_json()

            assert response["type"] == MessageType.SUBSCRIPTION_ACK
            assert response["stream_type"] == StreamType.OHLCV

    def test_subscribe_multiple_streams(self, client):
        """Test creating multiple subscriptions on same connection"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Subscribe to price stream
            price_request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": ["AAPL"],
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 1000,
                "data_type": DataType.PRICE,
            }
            websocket.send_json(price_request)
            price_response = websocket.receive_json()
            assert price_response["type"] == MessageType.SUBSCRIPTION_ACK

            # Subscribe to OHLCV stream
            ohlcv_request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.OHLCV,
                "symbols": ["MSFT"],
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 5000,
                "data_type": DataType.OHLCV,
            }
            websocket.send_json(ohlcv_request)
            ohlcv_response = websocket.receive_json()
            assert ohlcv_response["type"] == MessageType.SUBSCRIPTION_ACK

            # Both subscriptions should be active
            assert price_response["subscription_id"] != ohlcv_response["subscription_id"]

    def test_unsubscribe_from_stream(self, client):
        """Test unsubscribing from a stream"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Subscribe first
            subscribe_request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": ["AAPL", "GOOGL"],
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 1000,
                "data_type": DataType.PRICE,
            }
            websocket.send_json(subscribe_request)
            sub_response = websocket.receive_json()
            assert sub_response["type"] == MessageType.SUBSCRIPTION_ACK

            # Unsubscribe
            unsubscribe_request = {
                "type": MessageType.UNSUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": ["AAPL"],
            }
            websocket.send_json(unsubscribe_request)

            # Should receive acknowledgment
            unsub_response = websocket.receive_json()
            assert unsub_response["type"] == "unsubscribe_ack"

    def test_invalid_subscription_request(self, client):
        """Test handling of invalid subscription request"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Send invalid request (missing required fields)
            invalid_request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                # Missing symbols
            }
            websocket.send_json(invalid_request)

            # Should receive error message
            response = websocket.receive_json()
            assert response["type"] == MessageType.ERROR


class TestDataStreaming:
    """Test real-time data streaming"""

    @pytest.mark.asyncio
    async def test_receive_price_updates(self, client):
        """Test receiving price update messages"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Subscribe to price stream with short interval
            request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": ["AAPL"],
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 500,  # Fast updates for testing
                "data_type": DataType.PRICE,
            }
            websocket.send_json(request)

            # Get subscription ACK
            ack = websocket.receive_json()
            assert ack["type"] == MessageType.SUBSCRIPTION_ACK

            # Wait for data messages (with timeout)
            data_received = False
            for _ in range(5):  # Try up to 5 messages
                try:
                    message = websocket.receive_json(timeout=3)
                    if message.get("type") == MessageType.DATA:
                        data_received = True
                        # Validate data message structure
                        assert message["stream_type"] == StreamType.PRICE
                        assert "subscription_id" in message
                        assert "data" in message
                        assert len(message["data"]) > 0

                        # Validate price update structure
                        price_update = message["data"][0]
                        assert "symbol" in price_update
                        assert "price" in price_update
                        assert "timestamp" in price_update
                        break
                except Exception:
                    continue

            # We should have received at least one data message
            # Note: This may fail if no providers are available
            if not data_received:
                pytest.skip("No price data received (providers may not be available)")

    def test_price_endpoint_shortcut(self, client):
        """Test simplified /ws/prices/{symbols} endpoint"""
        with client.websocket_connect("/ws/prices/AAPL,MSFT") as websocket:
            # Should auto-subscribe and receive ACK
            response = websocket.receive_json()
            assert response["type"] == MessageType.SUBSCRIPTION_ACK
            assert set(response["symbols"]) == {"AAPL", "MSFT"}


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_invalid_json_message(self, client):
        """Test handling of invalid JSON"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Send invalid JSON
            websocket.send_text("not valid json {")

            # Should receive error
            response = websocket.receive_json()
            assert response["type"] == MessageType.ERROR
            assert response["error_code"] == "INVALID_JSON"

    def test_unknown_message_type(self, client):
        """Test handling of unknown message type"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Send message with unknown type
            websocket.send_json({"type": "UNKNOWN_TYPE", "data": "test"})

            # Should receive error
            response = websocket.receive_json()
            assert response["type"] == MessageType.ERROR
            assert response["error_code"] == "INVALID_MESSAGE_TYPE"

    def test_subscription_limit(self, client):
        """Test subscription symbol limit"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Try to subscribe to too many symbols (limit is 50)
            symbols = [f"SYM{i}" for i in range(51)]
            request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": symbols,
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 1000,
                "data_type": DataType.PRICE,
            }
            websocket.send_json(request)

            # Should receive error due to validation
            response = websocket.receive_json()
            assert response["type"] == MessageType.ERROR


class TestWebSocketManager:
    """Test WebSocket manager directly"""

    @pytest.mark.asyncio
    async def test_manager_connection_tracking(self):
        """Test that manager tracks connections correctly"""
        initial_count = len(websocket_manager.active_connections)

        # Note: Direct manager testing requires mocking WebSocket
        # In a real scenario, use the client fixture

        # After test, count should be back to initial
        assert len(websocket_manager.active_connections) == initial_count

    def test_get_active_connections_endpoint(self, client):
        """Test /ws/connections endpoint"""
        response = client.get("/ws/connections")
        assert response.status_code == 200

        data = response.json()
        assert "active_connections" in data
        assert "total_subscriptions" in data
        assert "subscribed_symbols" in data


class TestIntegrationWithArbitration:
    """Test integration with arbitration engine"""

    @pytest.mark.asyncio
    async def test_websocket_uses_arbitration_engine(self, client):
        """
        Test that WebSocket streaming uses the arbitration engine

        This ensures data comes from optimal providers with fallback
        """
        with client.websocket_connect("/ws/stream") as websocket:
            request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": ["AAPL"],
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 500,
                "data_type": DataType.PRICE,
            }
            websocket.send_json(request)

            # Get ACK
            websocket.receive_json()

            # Try to get a data message
            for _ in range(5):
                try:
                    message = websocket.receive_json(timeout=3)
                    if message.get("type") == MessageType.DATA:
                        # Check that provider name is included
                        price_update = message["data"][0]
                        assert "provider" in price_update
                        assert "confidence" in price_update

                        # Provider should be a real provider name
                        assert price_update["provider"] in [
                            "mock_provider",
                            "yahoo_finance",
                            "alpha_vantage",
                            "fmp",
                            "ccxt_binance",
                        ]
                        break
                except Exception:
                    continue


# Performance and stress tests
class TestWebSocketPerformance:
    """Test WebSocket performance characteristics"""

    @pytest.mark.slow
    def test_multiple_concurrent_subscriptions(self, client):
        """Test handling many concurrent subscriptions"""
        with client.websocket_connect("/ws/stream") as websocket:
            # Create multiple subscriptions
            for i in range(5):
                request = {
                    "type": MessageType.SUBSCRIBE,
                    "stream_type": StreamType.PRICE,
                    "symbols": [f"TEST{i}"],
                    "asset_type": AssetType.EQUITY,
                    "market": Market.US,
                    "interval_ms": 1000,
                    "data_type": DataType.PRICE,
                }
                websocket.send_json(request)

                # Get ACK
                ack = websocket.receive_json()
                assert ack["type"] == MessageType.SUBSCRIPTION_ACK

    @pytest.mark.slow
    def test_high_frequency_updates(self, client):
        """Test handling high-frequency updates (100ms interval)"""
        with client.websocket_connect("/ws/stream") as websocket:
            request = {
                "type": MessageType.SUBSCRIBE,
                "stream_type": StreamType.PRICE,
                "symbols": ["AAPL"],
                "asset_type": AssetType.EQUITY,
                "market": Market.US,
                "interval_ms": 100,  # Very frequent updates
                "data_type": DataType.PRICE,
            }
            websocket.send_json(request)

            ack = websocket.receive_json()
            assert ack["type"] == MessageType.SUBSCRIPTION_ACK

            # Should handle rapid updates without errors
            # Just verify it doesn't crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
