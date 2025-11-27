# Watchdog System Quick Reference

## 🚀 Quick Start

```python
from fiml.watchdog import watchdog_manager, EventFilter, Severity

# Initialize and start
await watchdog_manager.initialize()
await watchdog_manager.start()

# Subscribe to events
def handle_event(event):
    print(f"Alert: {event.description}")

subscription_id = watchdog_manager.subscribe_to_events(
    callback=handle_event,
    event_filter=EventFilter(severities=[Severity.HIGH, Severity.CRITICAL])
)

# Stop when done
await watchdog_manager.stop()
```

## 📊 8 Watchdog Types

| Watchdog | Purpose | Check Interval | Trigger |
|----------|---------|----------------|---------|
| **EarningsAnomaly** | Earnings beats/misses | 5 min | >10% deviation |
| **UnusualVolume** | Volume spikes | 1 min | >3x average |
| **WhaleMovement** | Large crypto transfers | 2 min | >$1M USD |
| **FundingRate** | Perpetual funding rates | 5 min | >0.1% or <-0.1% |
| **LiquidityDrop** | Order book depth | 3 min | >50% reduction |
| **CorrelationBreakdown** | Asset correlations | 10 min | Change >0.5 |
| **ExchangeOutage** | Exchange health | 1 min | HTTP errors/timeouts |
| **PriceAnomaly** | Rapid price moves | 30 sec | >5% in 1 min |

## 🎯 Event Types

```python
from fiml.watchdog import EventType

EventType.EARNINGS_ANOMALY      # Earnings surprise
EventType.UNUSUAL_VOLUME        # Volume spike
EventType.WHALE_MOVEMENT        # Large crypto transfer
EventType.FUNDING_SPIKE         # Extreme funding rate
EventType.LIQUIDITY_DROP        # Order book depth drop
EventType.CORRELATION_BREAK     # Correlation breakdown
EventType.EXCHANGE_OUTAGE       # Exchange/API issue
EventType.PRICE_ANOMALY         # Rapid price movement
EventType.FLASH_CRASH           # Extreme price drop
EventType.ARBITRAGE_OPPORTUNITY # Cross-exchange difference
```

## 📈 Severity Levels

```python
from fiml.watchdog import Severity

Severity.LOW       # Informational
Severity.MEDIUM    # Monitoring recommended
Severity.HIGH      # Attention required
Severity.CRITICAL  # Immediate action needed
```

## 🔍 Filtering Events

```python
from fiml.watchdog import EventFilter

# By severity
filter = EventFilter(severities=[Severity.HIGH, Severity.CRITICAL])

# By event type
filter = EventFilter(event_types=[EventType.PRICE_ANOMALY])

# By asset
filter = EventFilter(assets=["BTC", "ETH", "AAPL"])

# Combined
filter = EventFilter(
    event_types=[EventType.UNUSUAL_VOLUME],
    severities=[Severity.HIGH],
    assets=["TSLA"]
)

subscription_id = watchdog_manager.subscribe_to_events(
    callback=my_handler,
    event_filter=filter
)
```

## 🏥 Health Monitoring

```python
# Get health of all watchdogs
health = watchdog_manager.get_health()
for name, status in health.items():
    print(f"{name}: {status.status}")

# Get overall status
status = watchdog_manager.get_status()
print(f"Running: {status['running']}")
print(f"Healthy: {status['health_summary']['healthy']}")
```

## 📜 Event History

```python
# Get recent events
events = watchdog_manager.get_recent_events(limit=50)

# Get filtered history
critical_events = watchdog_manager.get_recent_events(
    event_filter=EventFilter(severities=[Severity.CRITICAL]),
    limit=100
)

# Get event statistics
stats = watchdog_manager.get_event_stats()
print(f"Total: {stats['total_events']}")
print(f"By type: {stats['events_by_type']}")
```

## ⚙️ Watchdog Control

```python
# Enable/disable specific watchdog
await watchdog_manager.disable_watchdog("whale_movement")
await watchdog_manager.enable_watchdog("whale_movement")

# Restart a watchdog
await watchdog_manager.restart_watchdog("price_anomaly")

# Get specific watchdog
watchdog = watchdog_manager.get_watchdog("unusual_volume")
print(f"Enabled: {watchdog.enabled}")
print(f"Running: {watchdog.is_running()}")

# List all watchdogs
watchdogs = watchdog_manager.list_watchdogs()
```

## 🔧 Configuration

```python
config = {
    "earnings_anomaly": {
        "enabled": True,
        "check_interval": 300,  # 5 minutes
    },
    "unusual_volume": {
        "enabled": True,
        "check_interval": 60,   # 1 minute
    },
    # ... configure others
}

manager = WatchdogManager(config=config)
```

## 📦 Event Structure

```python
{
    "event_id": "evt_1763887871.170377",
    "type": "price_anomaly",
    "severity": "high",
    "asset": {
        "symbol": "BTC",
        "asset_type": "crypto"
    },
    "description": "BTC rapid price movement: +7.5% in 1 min",
    "data": {
        "current_price": 45000,
        "past_price": 41860,
        "change_pct": 7.5
    },
    "timestamp": "2024-11-23T10:30:00Z",
    "watchdog": "price_anomaly"
}
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/test_watchdog.py -v

# Run specific test
pytest tests/test_watchdog.py::test_watchdog_manager_lifecycle -v

# Run demo
python examples/watchdog_demo.py
```

## 📚 Documentation

- **Full README**: `fiml/watchdog/README.md`
- **Implementation Summary**: `WATCHDOG_IMPLEMENTATION_SUMMARY.md`
- **Example**: `examples/watchdog_demo.py`
- **Tests**: `tests/test_watchdog.py`

## 🔗 Integration Points

```python
# Access arbitration engine
from fiml.arbitration.engine import arbitration_engine
data = await arbitration_engine.get_market_data(...)

# Access cache
from fiml.cache.manager import cache_manager
historical = await cache_manager.get(...)

# Access providers
from fiml.providers.registry import provider_registry
provider = provider_registry.get_provider(...)
```

## ⚡ Performance

- Event emission: <10ms
- Notification: <5ms
- Throughput: >1000 events/sec
- Memory: ~50MB for 1000 events

## 🚨 Error Handling

Watchdogs automatically:
- Retry failed checks (configurable)
- Track error counts
- Update health status
- Continue running on transient failures
- Log all errors

```python
# Configure retry behavior
watchdog = CustomWatchdog(
    check_interval=60,
    max_retries=3,
    retry_delay=5
)
```

## 📞 Support

- GitHub Issues: Report bugs/features
- Documentation: `fiml/watchdog/README.md`
- Examples: `examples/watchdog_demo.py`
- Tests: Reference implementations

## ✅ Test Status

**25/25 tests passing** ✅

- Models and Events: ✅
- Base Watchdog: ✅
- Event Stream: ✅
- Manager: ✅
- Detectors: ✅
- Integration: ✅
- Performance: ✅
