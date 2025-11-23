# Watchdog Event Intelligence System

A real-time event monitoring and alerting system for detecting market anomalies, unusual activity, and significant events across equities and crypto markets.

## Overview

The Watchdog system continuously monitors financial markets for 8 types of anomalies and events:

1. **Earnings Anomaly** - Significant earnings beats/misses (>10% deviation)
2. **Unusual Volume** - Volume spikes >3x average
3. **Whale Movement** - Large crypto transfers (>$1M)
4. **Funding Rate Spikes** - Extreme perpetual futures funding rates
5. **Liquidity Drops** - Order book depth reduction >50%
6. **Correlation Breakdown** - Asset correlation changes >0.5
7. **Exchange Outages** - API/exchange health issues
8. **Price Anomalies** - Rapid price movements (>5% in 1 min)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Watchdog Manager                        │
│  - Lifecycle coordination                                │
│  - Health monitoring                                     │
│  - Event aggregation                                     │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │                            │
        ▼                            ▼
┌──────────────┐            ┌─────────────────┐
│   Watchdogs  │            │  Event Stream   │
│  (8 types)   │───────────▶│  - Pub/Sub      │
│              │            │  - Persistence  │
│  - Earnings  │            │  - WebSocket    │
│  - Volume    │            └────────┬────────┘
│  - Whale     │                     │
│  - Funding   │                     │
│  - Liquidity │                     ▼
│  - Correlation│            ┌───────────────┐
│  - Exchange  │            │  Subscribers  │
│  - Price     │            │  - Callbacks  │
└──────────────┘            │  - Filters    │
                            └───────────────┘
```

## Quick Start

### Basic Usage

```python
from fiml.watchdog import watchdog_manager, EventFilter, Severity

# Initialize and start
await watchdog_manager.initialize()
await watchdog_manager.start()

# Subscribe to events
def handle_event(event):
    print(f"Alert: {event.description}")
    print(f"Severity: {event.severity.value}")
    print(f"Asset: {event.asset.symbol if event.asset else 'N/A'}")

subscription_id = watchdog_manager.subscribe_to_events(
    callback=handle_event,
    event_filter=EventFilter(
        severities=[Severity.HIGH, Severity.CRITICAL]
    )
)

# Let it run...
# await asyncio.sleep(3600)

# Stop when done
await watchdog_manager.stop()
```

### Filtering Events

```python
from fiml.watchdog import EventFilter, EventType, Severity

# Filter by event type
filter_price = EventFilter(
    event_types=[EventType.PRICE_ANOMALY, EventType.FLASH_CRASH]
)

# Filter by severity
filter_critical = EventFilter(
    severities=[Severity.CRITICAL]
)

# Filter by asset
filter_btc = EventFilter(
    assets=["BTC", "ETH"]
)

# Combine filters
filter_combined = EventFilter(
    event_types=[EventType.UNUSUAL_VOLUME],
    severities=[Severity.HIGH, Severity.CRITICAL],
    assets=["AAPL", "TSLA"]
)

subscription_id = watchdog_manager.subscribe_to_events(
    callback=handle_event,
    event_filter=filter_combined
)
```

### Health Monitoring

```python
# Get health of all watchdogs
health = watchdog_manager.get_health()

for name, health_status in health.items():
    print(f"{name}: {health_status.status}")
    print(f"  Events emitted: {health_status.events_emitted}")
    print(f"  Errors: {health_status.errors}")
    print(f"  Last check: {health_status.last_check}")

# Get overall system status
status = watchdog_manager.get_status()
print(f"Running: {status['running']}")
print(f"Total watchdogs: {status['total_watchdogs']}")
print(f"Healthy: {status['health_summary']['healthy']}")
```

### Event History

```python
# Get recent events
recent_events = watchdog_manager.get_recent_events(limit=50)

for event in recent_events:
    print(f"{event.timestamp}: {event.description}")

# Get filtered history
high_severity_events = watchdog_manager.get_recent_events(
    event_filter=EventFilter(severities=[Severity.HIGH, Severity.CRITICAL]),
    limit=100
)
```

## Configuration

Configure watchdogs via the manager initialization:

```python
config = {
    "earnings_anomaly": {
        "enabled": True,
        "check_interval": 300,  # 5 minutes
    },
    "unusual_volume": {
        "enabled": True,
        "check_interval": 60,  # 1 minute
    },
    "price_anomaly": {
        "enabled": True,
        "check_interval": 30,  # 30 seconds
    },
    # ... configure other watchdogs
}

manager = WatchdogManager(config=config)
```

### Per-Watchdog Control

```python
# Disable a watchdog
await watchdog_manager.disable_watchdog("whale_movement")

# Enable a watchdog
await watchdog_manager.enable_watchdog("whale_movement")

# Restart a watchdog
await watchdog_manager.restart_watchdog("price_anomaly")

# Get specific watchdog
watchdog = watchdog_manager.get_watchdog("unusual_volume")
print(f"Enabled: {watchdog.enabled}")
print(f"Running: {watchdog.is_running()}")
```

## Event Types

### WatchdogEvent Structure

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
        "change_pct": 7.5,
        "time_window_seconds": 60
    },
    "timestamp": "2024-11-23T10:30:00Z",
    "watchdog": "price_anomaly",
    "metadata": {}
}
```

### Event Types Enum

- `EARNINGS_ANOMALY` - Earnings surprise
- `UNUSUAL_VOLUME` - Volume spike
- `WHALE_MOVEMENT` - Large crypto transfer
- `FUNDING_SPIKE` - Extreme funding rate
- `LIQUIDITY_DROP` - Order book depth drop
- `CORRELATION_BREAK` - Correlation breakdown
- `EXCHANGE_OUTAGE` - Exchange/API issue
- `PRICE_ANOMALY` - Rapid price movement
- `FLASH_CRASH` - Extreme price drop
- `ARBITRAGE_OPPORTUNITY` - Cross-exchange price difference

### Severity Levels

- `LOW` - Minor event, informational
- `MEDIUM` - Notable event, monitoring recommended
- `HIGH` - Significant event, attention required
- `CRITICAL` - Severe event, immediate action needed

## Detector Details

### 1. Earnings Anomaly Watchdog

**Purpose**: Detect significant earnings beats/misses

**Check Interval**: 5 minutes (configurable)

**Triggers**:
- Actual EPS vs estimate deviation >10%
- Revenue surprises
- Guidance changes

**Event Data**:
```python
{
    "actual_eps": 2.50,
    "estimated_eps": 2.20,
    "surprise_pct": 13.6,
    "report_date": "2024-01-15",
    "revenue": 50000000000,
    "revenue_estimate": 48000000000
}
```

### 2. Unusual Volume Watchdog

**Purpose**: Detect abnormal trading volume

**Check Interval**: 1 minute

**Triggers**:
- Current volume >3x 30-day average
- Sustained high volume

**Event Data**:
```python
{
    "current_volume": 15000000,
    "avg_volume": 4500000,
    "volume_ratio": 3.33,
    "price_change_pct": 5.2,
    "price": 175.50
}
```

### 3. Whale Movement Watchdog

**Purpose**: Track large crypto wallet transfers

**Check Interval**: 2 minutes

**Triggers**:
- Transfers >$1M USD value
- Exchange inflows/outflows
- Whale accumulation patterns

**Event Data**:
```python
{
    "from": "0x123...",
    "to": "0x456...",
    "amount": 500.0,
    "usd_value": 15000000,
    "tx_hash": "0xabc..."
}
```

### 4. Funding Rate Watchdog

**Purpose**: Monitor perpetual futures funding rates

**Check Interval**: 5 minutes

**Triggers**:
- Funding rate >0.1% or <-0.1% per 8h
- Extreme positive/negative funding

**Event Data**:
```python
{
    "avg_funding_rate": 0.0015,
    "funding_rate_pct": 0.15,
    "by_exchange": {
        "binance": 0.0016,
        "bybit": 0.0014,
        "okx": 0.0015
    }
}
```

### 5. Liquidity Drop Watchdog

**Purpose**: Detect order book depth reductions

**Check Interval**: 3 minutes

**Triggers**:
- Order book depth drops >50%
- Bid-ask spread widening

**Event Data**:
```python
{
    "current_depth": 500000,
    "avg_depth": 1200000,
    "drop_pct": 58.3,
    "depth_ratio": 0.417
}
```

### 6. Correlation Breakdown Watchdog

**Purpose**: Identify correlation regime changes

**Check Interval**: 10 minutes

**Triggers**:
- 7-day vs 90-day correlation change >0.5
- Asset decoupling

**Monitored Pairs**:
- BTC/ETH
- SPY/QQQ
- GLD/TLT
- BTC/SPY

**Event Data**:
```python
{
    "asset1": "BTC",
    "asset2": "ETH",
    "recent_corr": 0.45,
    "hist_corr": 0.92,
    "change": 0.47
}
```

### 7. Exchange Outage Watchdog

**Purpose**: Monitor exchange and API health

**Check Interval**: 1 minute

**Triggers**:
- HTTP errors (non-200 status)
- Response time >threshold
- Timeouts

**Monitored Exchanges**:
- Binance
- Coinbase
- Kraken

**Event Data**:
```python
{
    "exchange": "binance",
    "status_code": 503,
    "response_time_ms": 8500
}
```

### 8. Price Anomaly Watchdog

**Purpose**: Detect rapid price movements and flash crashes

**Check Interval**: 30 seconds

**Triggers**:
- Price change >5% in 1 minute
- Flash crashes (>10% drop)
- Cross-exchange arbitrage

**Event Data**:
```python
{
    "current_price": 44500,
    "past_price": 42000,
    "change_pct": 5.95,
    "time_window_seconds": 60
}
```

## Event Stream

The event stream handles pub/sub distribution, persistence, and broadcasting.

### Features

- **In-memory event buffer** (circular, configurable size)
- **Redis Streams persistence** (optional)
- **WebSocket broadcasting** (optional)
- **Subscription filtering**
- **Event statistics tracking**

### Persistence

Events are automatically persisted to Redis Streams if enabled:

```python
# Events stored in Redis Stream: "watchdog:events"
# Max length: 10,000 events
# TTL: Configured by Redis

# Retrieve persisted events
events = await event_stream.get_persisted_events(
    start_id="-",  # From beginning
    count=100
)
```

### WebSocket Broadcasting

Events can be broadcast to WebSocket clients:

```python
# WebSocket message format
{
    "type": "watchdog_event",
    "event": {
        "event_id": "...",
        "type": "price_anomaly",
        "severity": "high",
        ...
    }
}
```

## Creating Custom Watchdogs

Extend `BaseWatchdog` to create custom detectors:

```python
from fiml.watchdog import BaseWatchdog, WatchdogEvent, EventType, Severity
from fiml.core.models import Asset, AssetType

class CustomWatchdog(BaseWatchdog):
    def __init__(self, check_interval: int = 60, **kwargs):
        super().__init__(check_interval=check_interval, **kwargs)
        self.threshold = 10.0
    
    @property
    def name(self) -> str:
        return "custom_detector"
    
    async def check(self) -> Optional[WatchdogEvent]:
        """Implement your detection logic"""
        # Fetch data
        data = await self.fetch_data()
        
        # Detect anomaly
        if self.is_anomaly(data):
            return WatchdogEvent(
                type=EventType.PRICE_ANOMALY,  # Or custom type
                severity=Severity.HIGH,
                asset=Asset(symbol="BTC", asset_type=AssetType.CRYPTO),
                description="Custom anomaly detected",
                data={"value": data},
                watchdog=self.name,
            )
        
        return None
    
    async def fetch_data(self):
        """Fetch data from providers/cache"""
        # Your implementation
        pass
    
    def is_anomaly(self, data) -> bool:
        """Detect if data indicates anomaly"""
        # Your logic
        return False
```

Register custom watchdog:

```python
# Add to orchestrator
manager = WatchdogManager()
custom = CustomWatchdog()
custom.set_event_stream(manager._event_stream)
manager._watchdogs["custom_detector"] = custom
```

## Testing

Run the test suite:

```bash
pytest tests/test_watchdog.py -v
```

Tests cover:
- Event creation and filtering
- Watchdog lifecycle (start/stop)
- Event emission and subscription
- Error handling and recovery
- Health monitoring
- Manager orchestration
- High-frequency event handling
- Concurrent execution

## Performance

- **Event emission latency**: <10ms
- **Subscription notification**: <5ms
- **Check intervals**: 30s to 10min (configurable)
- **Memory usage**: ~50MB for 1000 events in history
- **Throughput**: >1000 events/second

## Integration

### With Arbitration Engine

Watchdogs use the arbitration engine for market data:

```python
from fiml.arbitration.engine import arbitration_engine

current_data = await arbitration_engine.get_market_data(
    asset=asset,
    data_type=DataType.PRICE,
    market=Market.CRYPTO,
)
```

### With Cache System

Access historical data for analysis:

```python
from fiml.cache.manager import cache_manager

historical_data = await cache_manager.get(
    key=f"ohlcv:{symbol}:1d",
    ttl=3600
)
```

### With WebSocket Manager

Broadcast events to connected clients:

```python
from fiml.websocket.manager import websocket_manager

event_stream.set_websocket_manager(websocket_manager)
```

## Best Practices

1. **Event Filtering**: Subscribe only to events you need
2. **Check Intervals**: Balance timeliness vs API rate limits
3. **Error Handling**: Watchdogs auto-retry on transient failures
4. **Health Monitoring**: Regularly check watchdog health status
5. **Event History**: Use for backtesting and analysis
6. **Graceful Shutdown**: Always stop manager properly

## Troubleshooting

### Watchdog Not Emitting Events

- Check if watchdog is enabled: `watchdog.enabled`
- Verify data source availability
- Check health status: `watchdog.get_health()`
- Review logs for errors

### High Error Rate

- Check API rate limits
- Verify provider connectivity
- Review retry configuration
- Check health status

### Missing Events

- Verify event filter criteria
- Check subscription is active
- Review event history
- Check severity thresholds

## License

Apache 2.0

## Contributing

See CONTRIBUTING.md for development guidelines.
