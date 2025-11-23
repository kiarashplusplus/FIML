"""
Comprehensive tests for the Watchdog event intelligence system

Tests cover:
- Base watchdog functionality
- Event emission and filtering
- Individual detector logic
- Orchestrator lifecycle
- Error handling and recovery
"""

import asyncio
from typing import List

import pytest

from fiml.core.models import Asset, AssetType
from fiml.watchdog import (
    BaseWatchdog,
    EarningsAnomalyWatchdog,
    EventFilter,
    EventStream,
    EventType,
    ExchangeOutageWatchdog,
    PriceAnomalyWatchdog,
    Severity,
    UnusualVolumeWatchdog,
    WatchdogEvent,
    WatchdogManager,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def event_stream():
    """Create event stream for testing"""
    stream = EventStream(enable_persistence=False, enable_websocket=False)
    return stream


@pytest.fixture
async def initialized_event_stream():
    """Create and initialize event stream"""
    stream = EventStream(enable_persistence=False, enable_websocket=False)
    await stream.initialize()
    return stream


@pytest.fixture
def sample_event():
    """Create a sample watchdog event"""
    return WatchdogEvent(
        type=EventType.PRICE_ANOMALY,
        severity=Severity.HIGH,
        asset=Asset(symbol="BTC", asset_type=AssetType.CRYPTO),
        description="Test event",
        data={"test": "data"},
        watchdog="test_watchdog",
    )


# ============================================================================
# Mock Watchdog for Testing
# ============================================================================


class MockWatchdog(BaseWatchdog):
    """Mock watchdog for testing base functionality"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.check_count = 0
        self.should_emit_event = False
        self.should_fail = False

    @property
    def name(self) -> str:
        return "mock_watchdog"

    async def check(self) -> WatchdogEvent | None:
        """Mock check method"""
        self.check_count += 1

        if self.should_fail:
            raise Exception("Mock check failure")

        if self.should_emit_event:
            return WatchdogEvent(
                type=EventType.PRICE_ANOMALY,
                severity=Severity.MEDIUM,
                asset=Asset(symbol="TEST", asset_type=AssetType.EQUITY),
                description="Mock event",
                data={"check_count": self.check_count},
                watchdog=self.name,
            )

        return None


# ============================================================================
# Test Models
# ============================================================================


def test_watchdog_event_creation(sample_event):
    """Test creating watchdog events"""
    assert sample_event.type == EventType.PRICE_ANOMALY
    assert sample_event.severity == Severity.HIGH
    assert sample_event.asset.symbol == "BTC"
    assert sample_event.watchdog == "test_watchdog"


def test_event_filter_matching(sample_event):
    """Test event filter matching"""
    # Match all
    filter_all = EventFilter()
    assert filter_all.matches(sample_event)

    # Match by type
    filter_type = EventFilter(event_types=[EventType.PRICE_ANOMALY])
    assert filter_type.matches(sample_event)

    filter_wrong_type = EventFilter(event_types=[EventType.EARNINGS_ANOMALY])
    assert not filter_wrong_type.matches(sample_event)

    # Match by severity
    filter_severity = EventFilter(severities=[Severity.HIGH])
    assert filter_severity.matches(sample_event)

    filter_wrong_severity = EventFilter(severities=[Severity.LOW])
    assert not filter_wrong_severity.matches(sample_event)

    # Match by asset
    filter_asset = EventFilter(assets=["BTC"])
    assert filter_asset.matches(sample_event)

    filter_wrong_asset = EventFilter(assets=["ETH"])
    assert not filter_wrong_asset.matches(sample_event)


def test_event_to_dict(sample_event):
    """Test event serialization"""
    event_dict = sample_event.to_dict()

    assert event_dict["type"] == "price_anomaly"
    assert event_dict["severity"] == "high"
    assert event_dict["description"] == "Test event"
    assert event_dict["data"]["test"] == "data"


# ============================================================================
# Test BaseWatchdog
# ============================================================================


@pytest.mark.asyncio
async def test_base_watchdog_lifecycle():
    """Test watchdog start/stop lifecycle"""
    watchdog = MockWatchdog(check_interval=1)
    event_stream = EventStream(enable_persistence=False, enable_websocket=False)
    await event_stream.initialize()
    watchdog.set_event_stream(event_stream)

    # Start watchdog
    await watchdog.start()
    assert watchdog.is_running()
    assert watchdog.get_health().status == "healthy"

    # Let it run for a bit
    await asyncio.sleep(2.5)

    # Should have performed checks
    assert watchdog.check_count >= 2

    # Stop watchdog
    await watchdog.stop()
    assert not watchdog.is_running()

    await event_stream.shutdown()


@pytest.mark.asyncio
async def test_base_watchdog_event_emission():
    """Test event emission from watchdog"""
    watchdog = MockWatchdog(check_interval=1)
    event_stream = EventStream(enable_persistence=False, enable_websocket=False)
    await event_stream.initialize()
    watchdog.set_event_stream(event_stream)

    # Track emitted events
    emitted_events: List[WatchdogEvent] = []

    def event_handler(event: WatchdogEvent):
        emitted_events.append(event)

    event_stream.subscribe(callback=event_handler)

    # Configure watchdog to emit events
    watchdog.should_emit_event = True

    # Start watchdog
    await watchdog.start()
    await asyncio.sleep(2.5)
    await watchdog.stop()

    # Should have emitted events
    assert len(emitted_events) >= 2
    assert all(e.watchdog == "mock_watchdog" for e in emitted_events)

    await event_stream.shutdown()


@pytest.mark.asyncio
async def test_base_watchdog_error_handling():
    """Test watchdog error handling and retry"""
    watchdog = MockWatchdog(check_interval=1, max_retries=2, retry_delay=0)
    event_stream = EventStream(enable_persistence=False, enable_websocket=False)
    await event_stream.initialize()
    watchdog.set_event_stream(event_stream)

    # Configure to fail
    watchdog.should_fail = True

    await watchdog.start()
    await asyncio.sleep(2.5)

    # Should have degraded or unhealthy status
    health = watchdog.get_health()
    assert health.status in ["degraded", "unhealthy"]
    assert health.errors > 0

    await watchdog.stop()
    await event_stream.shutdown()


@pytest.mark.asyncio
async def test_base_watchdog_disabled():
    """Test that disabled watchdog doesn't start"""
    watchdog = MockWatchdog(enabled=False)
    event_stream = EventStream(enable_persistence=False, enable_websocket=False)
    await event_stream.initialize()
    watchdog.set_event_stream(event_stream)

    await watchdog.start()

    # Should not be running
    assert not watchdog.is_running()
    assert watchdog.check_count == 0

    await event_stream.shutdown()


# ============================================================================
# Test EventStream
# ============================================================================


@pytest.mark.asyncio
async def test_event_stream_emit_and_subscribe(initialized_event_stream, sample_event):
    """Test event emission and subscription"""
    events_received: List[WatchdogEvent] = []

    def handler(event: WatchdogEvent):
        events_received.append(event)

    # Subscribe
    sub_id = initialized_event_stream.subscribe(callback=handler)

    # Emit event
    await initialized_event_stream.emit(sample_event)

    # Wait briefly
    await asyncio.sleep(0.1)

    # Should have received event
    assert len(events_received) == 1
    assert events_received[0].type == EventType.PRICE_ANOMALY

    # Unsubscribe
    assert initialized_event_stream.unsubscribe(sub_id)

    await initialized_event_stream.shutdown()


@pytest.mark.asyncio
async def test_event_stream_filtering(initialized_event_stream):
    """Test event stream filtering"""
    high_severity_events: List[WatchdogEvent] = []
    all_events: List[WatchdogEvent] = []

    def high_handler(event: WatchdogEvent):
        high_severity_events.append(event)

    def all_handler(event: WatchdogEvent):
        all_events.append(event)

    # Subscribe with filter
    initialized_event_stream.subscribe(
        callback=high_handler,
        event_filter=EventFilter(severities=[Severity.HIGH, Severity.CRITICAL])
    )

    # Subscribe to all
    initialized_event_stream.subscribe(callback=all_handler)

    # Emit events with different severities
    events = [
        WatchdogEvent(
            type=EventType.PRICE_ANOMALY,
            severity=Severity.LOW,
            description="Low severity",
            watchdog="test",
        ),
        WatchdogEvent(
            type=EventType.PRICE_ANOMALY,
            severity=Severity.HIGH,
            description="High severity",
            watchdog="test",
        ),
        WatchdogEvent(
            type=EventType.PRICE_ANOMALY,
            severity=Severity.CRITICAL,
            description="Critical severity",
            watchdog="test",
        ),
    ]

    for event in events:
        await initialized_event_stream.emit(event)

    await asyncio.sleep(0.1)

    # Check results
    assert len(all_events) == 3
    assert len(high_severity_events) == 2  # Only HIGH and CRITICAL

    await initialized_event_stream.shutdown()


@pytest.mark.asyncio
async def test_event_stream_history(initialized_event_stream):
    """Test event history tracking"""
    # Emit multiple events
    for i in range(5):
        event = WatchdogEvent(
            type=EventType.PRICE_ANOMALY,
            severity=Severity.MEDIUM,
            description=f"Event {i}",
            watchdog="test",
        )
        await initialized_event_stream.emit(event)

    # Get history
    history = initialized_event_stream.get_history(limit=10)

    assert len(history) == 5
    # Should be newest first
    assert "Event 4" in history[0].description

    await initialized_event_stream.shutdown()


@pytest.mark.asyncio
async def test_event_stream_stats(initialized_event_stream):
    """Test event stream statistics"""
    # Emit various events
    events = [
        WatchdogEvent(type=EventType.PRICE_ANOMALY, severity=Severity.HIGH, description="1", watchdog="test"),
        WatchdogEvent(type=EventType.PRICE_ANOMALY, severity=Severity.LOW, description="2", watchdog="test"),
        WatchdogEvent(type=EventType.UNUSUAL_VOLUME, severity=Severity.MEDIUM, description="3", watchdog="test"),
    ]

    for event in events:
        await initialized_event_stream.emit(event)

    # Get stats
    stats = initialized_event_stream.get_stats()

    assert stats["total_events"] == 3
    assert stats["events_by_type"]["price_anomaly"] == 2
    assert stats["events_by_type"]["unusual_volume"] == 1
    assert stats["events_by_severity"]["high"] == 1
    assert stats["events_by_severity"]["medium"] == 1
    assert stats["events_by_severity"]["low"] == 1

    await initialized_event_stream.shutdown()


# ============================================================================
# Test WatchdogManager
# ============================================================================


@pytest.mark.asyncio
async def test_watchdog_manager_initialization():
    """Test watchdog manager initialization"""
    manager = WatchdogManager()

    await manager.initialize()

    assert manager._initialized
    assert len(manager._watchdogs) == 8  # All 8 watchdogs

    # Check all watchdogs are registered
    watchdog_names = manager.list_watchdogs()
    assert "earnings_anomaly" in watchdog_names
    assert "unusual_volume" in watchdog_names
    assert "price_anomaly" in watchdog_names

    await manager.stop()


@pytest.mark.asyncio
async def test_watchdog_manager_lifecycle():
    """Test watchdog manager start/stop"""
    manager = WatchdogManager()

    await manager.initialize()
    await manager.start()

    status = manager.get_status()
    assert status["running"]
    assert status["running_watchdogs"] > 0

    await manager.stop()

    status = manager.get_status()
    assert not status["running"]


@pytest.mark.asyncio
async def test_watchdog_manager_health_monitoring():
    """Test health monitoring"""
    manager = WatchdogManager()
    await manager.initialize()

    health = manager.get_health()

    # Should have health for all watchdogs
    assert len(health) == 8

    # All should be in initialized or healthy state
    for name, h in health.items():
        assert h.status in ["initialized", "healthy"]

    await manager.stop()


@pytest.mark.asyncio
async def test_watchdog_manager_enable_disable():
    """Test enabling/disabling individual watchdogs"""
    manager = WatchdogManager()
    await manager.initialize()

    # Disable a watchdog
    success = await manager.disable_watchdog("price_anomaly")
    assert success

    watchdog = manager.get_watchdog("price_anomaly")
    assert not watchdog.enabled

    # Enable it back
    success = await manager.enable_watchdog("price_anomaly")
    assert success
    assert watchdog.enabled

    await manager.stop()


@pytest.mark.asyncio
async def test_watchdog_manager_event_subscription():
    """Test subscribing to events through manager"""
    manager = WatchdogManager()
    await manager.initialize()

    events_received: List[WatchdogEvent] = []

    def handler(event: WatchdogEvent):
        events_received.append(event)

    # Subscribe
    sub_id = manager.subscribe_to_events(
        callback=handler,
        event_filter=EventFilter(severities=[Severity.HIGH, Severity.CRITICAL])
    )

    # Manually emit an event for testing
    event = WatchdogEvent(
        type=EventType.PRICE_ANOMALY,
        severity=Severity.HIGH,
        description="Test high severity",
        watchdog="test",
    )
    await manager._event_stream.emit(event)

    await asyncio.sleep(0.1)

    assert len(events_received) == 1

    # Unsubscribe
    assert manager.unsubscribe_from_events(sub_id)

    await manager.stop()


# ============================================================================
# Test Individual Detectors
# ============================================================================


@pytest.mark.asyncio
async def test_earnings_anomaly_detector():
    """Test earnings anomaly watchdog"""
    watchdog = EarningsAnomalyWatchdog(check_interval=60)

    assert watchdog.name == "earnings_anomaly"

    # Test check (will return None without real data)
    result = await watchdog.check()
    assert result is None  # No real data available


@pytest.mark.asyncio
async def test_unusual_volume_detector():
    """Test unusual volume watchdog"""
    watchdog = UnusualVolumeWatchdog(check_interval=60)

    assert watchdog.name == "unusual_volume"

    result = await watchdog.check()
    assert result is None  # No arbitration engine data


@pytest.mark.asyncio
async def test_exchange_outage_detector():
    """Test exchange outage watchdog"""
    watchdog = ExchangeOutageWatchdog(check_interval=60)

    assert watchdog.name == "exchange_outage"

    # This one actually checks real endpoints
    # We'll just verify it runs without crashing
    await watchdog.check()
    # Result could be None or an event depending on actual exchange status


@pytest.mark.asyncio
async def test_price_anomaly_detector_initialization():
    """Test price anomaly watchdog initialization"""
    watchdog = PriceAnomalyWatchdog(check_interval=30)

    assert watchdog.name == "price_anomaly"
    assert watchdog._rapid_move_threshold == 5.0
    assert len(watchdog._monitored_symbols) > 0


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_event_flow():
    """Test complete event flow from watchdog to subscriber"""
    # Create manager
    manager = WatchdogManager()
    await manager.initialize()

    # Track events
    events_received: List[WatchdogEvent] = []

    def handler(event: WatchdogEvent):
        events_received.append(event)

    # Subscribe to all events
    manager.subscribe_to_events(callback=handler)

    # Manually trigger an event by emitting directly
    event = WatchdogEvent(
        type=EventType.PRICE_ANOMALY,
        severity=Severity.CRITICAL,
        asset=Asset(symbol="BTC", asset_type=AssetType.CRYPTO),
        description="Test critical event",
        watchdog="test",
    )

    await manager._event_stream.emit(event)
    await asyncio.sleep(0.2)

    # Should have received the event
    assert len(events_received) == 1
    assert events_received[0].severity == Severity.CRITICAL

    # Check stats
    stats = manager.get_event_stats()
    assert stats["total_events"] >= 1

    await manager.stop()


@pytest.mark.asyncio
async def test_concurrent_watchdog_execution():
    """Test multiple watchdogs running concurrently"""
    manager = WatchdogManager()
    await manager.initialize()

    # Start all watchdogs
    await manager.start()

    # Let them run briefly
    await asyncio.sleep(2)

    # Check that multiple watchdogs have been active
    health = manager.get_health()

    # At least some should show activity
    sum(1 for h in health.values() if h.last_check is not None)

    # Note: Some watchdogs may not emit events due to lack of real data,
    # but they should still be checking

    await manager.stop()


@pytest.mark.asyncio
async def test_watchdog_restart():
    """Test restarting a specific watchdog"""
    manager = WatchdogManager()
    await manager.initialize()
    await manager.start()

    # Restart a watchdog
    success = await manager.restart_watchdog("price_anomaly")
    assert success

    # Should still be running
    watchdog = manager.get_watchdog("price_anomaly")
    await asyncio.sleep(0.5)
    assert watchdog.is_running()

    await manager.stop()


# ============================================================================
# Performance and Stress Tests
# ============================================================================


@pytest.mark.asyncio
async def test_high_frequency_event_emission():
    """Test handling high-frequency event emission"""
    stream = EventStream(enable_persistence=False, enable_websocket=False)
    await stream.initialize()

    events_received = []

    def handler(event: WatchdogEvent):
        events_received.append(event)

    stream.subscribe(callback=handler)

    # Emit many events quickly
    for i in range(100):
        event = WatchdogEvent(
            type=EventType.PRICE_ANOMALY,
            severity=Severity.LOW,
            description=f"Event {i}",
            watchdog="stress_test",
        )
        await stream.emit(event)

    await asyncio.sleep(0.5)

    # Should handle all events
    assert len(events_received) == 100

    await stream.shutdown()


# ============================================================================
# Error Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_watchdog_graceful_degradation():
    """Test watchdog continues after transient errors"""
    watchdog = MockWatchdog(check_interval=1, max_retries=2, retry_delay=0)
    event_stream = EventStream(enable_persistence=False, enable_websocket=False)
    await event_stream.initialize()
    watchdog.set_event_stream(event_stream)

    events = []
    event_stream.subscribe(lambda e: events.append(e))

    await watchdog.start()

    # Let it run successfully
    await asyncio.sleep(1.5)
    initial_checks = watchdog.check_count

    # Cause failures
    watchdog.should_fail = True
    await asyncio.sleep(2)

    # Recover
    watchdog.should_fail = False
    watchdog.should_emit_event = True
    await asyncio.sleep(1.5)

    # Should have recovered and continued
    assert watchdog.check_count > initial_checks

    await watchdog.stop()
    await event_stream.shutdown()
