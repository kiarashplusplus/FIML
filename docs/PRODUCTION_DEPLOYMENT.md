# Production Deployment Guide for Workers and Watchdogs

## Overview

FIML now includes 8 production-ready workers and 8 watchdogs with comprehensive configuration, monitoring, and health checks.

## Workers (8 Total)

### Available Workers

1. **FundamentalsWorker** - Financial fundamentals analysis
2. **TechnicalWorker** - Technical indicators and chart patterns
3. **MacroWorker** - Macroeconomic factors analysis
4. **SentimentWorker** - News sentiment analysis
5. **CorrelationWorker** - Asset correlation analysis
6. **RiskWorker** - Risk metrics and VaR calculations
7. **NewsWorker** - News event extraction and impact assessment
8. **OptionsWorker** *(NEW)* - Options market analysis and implied volatility

### Production Configuration

#### Worker Pool Settings

```python
# Environment variables or .env file
WORKER_POOL_SIZE=8  # Number of worker instances per type
WORKER_MAX_CONCURRENT_TASKS=50  # Max concurrent tasks per worker
WORKER_TASK_TIMEOUT=120  # Task timeout in seconds (2 minutes)
WORKER_RETRY_ATTEMPTS=3  # Number of retry attempts for failed tasks
WORKER_RETRY_DELAY=5  # Delay between retries in seconds
WORKER_HEALTH_CHECK_INTERVAL=60  # Health check interval in seconds
WORKER_MEMORY_LIMIT_MB=2048  # Memory limit per worker in MB
WORKER_CPU_LIMIT=2.0  # CPU cores limit per worker
```

#### Individual Worker Control

Enable or disable specific workers:

```python
ENABLE_FUNDAMENTALS_WORKER=true
ENABLE_TECHNICAL_WORKER=true
ENABLE_MACRO_WORKER=true
ENABLE_SENTIMENT_WORKER=true
ENABLE_CORRELATION_WORKER=true
ENABLE_RISK_WORKER=true
ENABLE_NEWS_WORKER=true
ENABLE_OPTIONS_WORKER=true
```

### Worker Health Monitoring

The system includes built-in health monitoring with metrics:

```python
from fiml.agents.health import worker_health_monitor

# Get health summary
summary = worker_health_monitor.get_health_summary()

# Get specific worker metrics
metrics = worker_health_monitor.get_metrics("fund_0")

# Get unhealthy workers
unhealthy = worker_health_monitor.get_unhealthy_workers()
```

### Worker Metrics

Each worker tracks:
- Tasks completed/failed/timeout
- Execution times (min/max/avg)
- Memory and CPU usage
- Success rate and error rate
- Last heartbeat timestamp
- Recent error messages

### Circuit Breaker Pattern

Workers implement automatic circuit breaker logic:
- Opens after 5 consecutive failures
- Half-open state after 60 seconds
- Automatically closes on successful recovery

## Watchdogs (8 Total)

### Available Watchdogs

1. **EarningsAnomalyWatchdog** - Earnings beats/misses detection
2. **UnusualVolumeWatchdog** - Volume spike detection
3. **WhaleMovementWatchdog** - Large crypto transfers
4. **FundingRateWatchdog** - Perpetual funding rate extremes
5. **LiquidityDropWatchdog** - Order book depth monitoring
6. **CorrelationBreakdownWatchdog** - Correlation shift detection
7. **ExchangeOutageWatchdog** - Exchange health monitoring
8. **PriceAnomalyWatchdog** - Rapid price movement detection

### Production Configuration

#### Global Watchdog Settings

```python
WATCHDOG_GLOBAL_ENABLED=true  # Master switch
WATCHDOG_EVENT_STREAM_ENABLED=true  # Enable event streaming
WATCHDOG_EVENT_PERSISTENCE=true  # Persist events to Redis
WATCHDOG_WEBSOCKET_BROADCAST=true  # Broadcast via WebSocket
WATCHDOG_MAX_EVENTS_IN_MEMORY=1000  # Circular buffer size
WATCHDOG_HEALTH_CHECK_INTERVAL=60  # Health check interval
```

#### Individual Watchdog Control

Enable or disable specific watchdogs:

```python
ENABLE_EARNINGS_ANOMALY_WATCHDOG=true
ENABLE_UNUSUAL_VOLUME_WATCHDOG=true
ENABLE_WHALE_MOVEMENT_WATCHDOG=true
ENABLE_FUNDING_RATE_WATCHDOG=true
ENABLE_LIQUIDITY_DROP_WATCHDOG=true
ENABLE_CORRELATION_BREAKDOWN_WATCHDOG=true
ENABLE_EXCHANGE_OUTAGE_WATCHDOG=true
ENABLE_PRICE_ANOMALY_WATCHDOG=true
```

#### Check Intervals

Configure how often each watchdog checks for anomalies:

```python
EARNINGS_ANOMALY_CHECK_INTERVAL=300  # 5 minutes
UNUSUAL_VOLUME_CHECK_INTERVAL=60  # 1 minute
WHALE_MOVEMENT_CHECK_INTERVAL=120  # 2 minutes
FUNDING_RATE_CHECK_INTERVAL=300  # 5 minutes
LIQUIDITY_DROP_CHECK_INTERVAL=180  # 3 minutes
CORRELATION_BREAKDOWN_CHECK_INTERVAL=600  # 10 minutes
EXCHANGE_OUTAGE_CHECK_INTERVAL=60  # 1 minute
PRICE_ANOMALY_CHECK_INTERVAL=30  # 30 seconds
```

#### Alert Thresholds

Fine-tune detection sensitivity:

```python
EARNINGS_SURPRISE_THRESHOLD_PCT=10.0  # Earnings surprise %
UNUSUAL_VOLUME_MULTIPLIER=3.0  # 3x average volume
WHALE_MOVEMENT_MIN_USD=1000000.0  # $1M minimum
FUNDING_RATE_THRESHOLD_PCT=0.1  # 0.1% threshold
LIQUIDITY_DROP_THRESHOLD_PCT=50.0  # 50% drop
CORRELATION_CHANGE_THRESHOLD=0.5  # 0.5 correlation change
PRICE_ANOMALY_THRESHOLD_PCT=5.0  # 5% price movement
```

### Watchdog Health Monitoring

The system includes built-in health monitoring:

```python
from fiml.watchdog.health import watchdog_health_monitor

# Get health summary
summary = watchdog_health_monitor.get_health_summary()

# Get specific watchdog metrics
metrics = watchdog_health_monitor.get_metrics("earnings_anomaly")

# Get unhealthy watchdogs
unhealthy = watchdog_health_monitor.get_unhealthy_watchdogs()

# Get stale watchdogs (not checking recently)
stale = watchdog_health_monitor.get_stale_watchdogs(max_age_seconds=300)
```

### Watchdog Metrics

Each watchdog tracks:
- Checks performed/failed
- Events detected by severity
- Check execution times (min/max/avg)
- Success rate and detection rate
- Last check and last event timestamps
- Consecutive failure count

## Usage Examples

### Initialize Workers

```python
from fiml.agents.orchestrator import AgentOrchestrator
from fiml.core.models import Asset, AssetType

# Initialize orchestrator (reads config automatically)
orchestrator = AgentOrchestrator()
await orchestrator.initialize()

# Analyze an asset with all enabled workers
asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
results = await orchestrator.analyze_asset(asset)

# Analyze with specific workers only
results = await orchestrator.analyze_asset(
    asset, 
    agents=["fundamentals", "technical", "options"]
)

# Shutdown
await orchestrator.shutdown()
```

### Initialize Watchdogs

```python
from fiml.watchdog import watchdog_manager

# Initialize manager (reads config automatically)
await watchdog_manager.initialize()

# Start monitoring
await watchdog_manager.start()

# Subscribe to events
def handle_critical_event(event):
    print(f"CRITICAL: {event.description}")

watchdog_manager.subscribe_to_events(
    callback=handle_critical_event,
    event_filter={"severities": ["critical"]}
)

# Check health
health = watchdog_manager.get_health()
status = watchdog_manager.get_status()

# Stop monitoring
await watchdog_manager.stop()
```

### Health Monitoring Dashboard

```python
from fiml.agents.health import worker_health_monitor
from fiml.watchdog.health import watchdog_health_monitor

# Get overall health
worker_summary = worker_health_monitor.get_health_summary()
watchdog_summary = watchdog_health_monitor.get_health_summary()

print(f"Workers: {worker_summary['healthy_workers']}/{worker_summary['total_workers']} healthy")
print(f"Watchdogs: {watchdog_summary['healthy_watchdogs']}/{watchdog_summary['enabled_watchdogs']} healthy")

# Check for issues
unhealthy_workers = worker_health_monitor.get_unhealthy_workers()
unhealthy_watchdogs = watchdog_health_monitor.get_unhealthy_watchdogs()

if unhealthy_workers:
    print(f"Unhealthy workers: {', '.join(unhealthy_workers)}")

if unhealthy_watchdogs:
    print(f"Unhealthy watchdogs: {', '.join(unhealthy_watchdogs)}")
```

## Production Deployment Checklist

### Pre-Deployment

- [ ] Configure production environment variables in `.env`
- [ ] Set appropriate worker pool sizes based on load
- [ ] Configure watchdog check intervals and thresholds
- [ ] Set up Redis for caching and event persistence
- [ ] Set up PostgreSQL for L2 cache and sessions
- [ ] Configure Azure OpenAI credentials
- [ ] Configure data provider API keys
- [ ] Set up Sentry for error tracking
- [ ] Set up Prometheus for metrics

### Deployment

- [ ] Deploy application with production configuration
- [ ] Initialize worker orchestrator on startup
- [ ] Initialize watchdog manager on startup
- [ ] Verify all enabled workers are healthy
- [ ] Verify all enabled watchdogs are running
- [ ] Test health monitoring endpoints
- [ ] Set up monitoring dashboards

### Post-Deployment

- [ ] Monitor worker health metrics
- [ ] Monitor watchdog health metrics
- [ ] Review event logs and alerts
- [ ] Tune thresholds based on production data
- [ ] Set up alerting for unhealthy components
- [ ] Review and adjust resource limits

## Monitoring Integration

### Prometheus Metrics

Workers and watchdogs expose metrics for Prometheus:

```python
# Worker metrics
worker_tasks_total{worker_type="fundamentals", status="success"}
worker_tasks_total{worker_type="fundamentals", status="failed"}
worker_execution_seconds{worker_type="fundamentals", quantile="0.5"}
worker_health_status{worker_id="fund_0"}

# Watchdog metrics
watchdog_checks_total{watchdog="earnings_anomaly", status="success"}
watchdog_events_total{watchdog="earnings_anomaly", severity="critical"}
watchdog_check_seconds{watchdog="earnings_anomaly", quantile="0.95"}
watchdog_health_status{watchdog="earnings_anomaly"}
```

### Health Endpoints

```bash
# Check worker health
GET /health/workers

# Check watchdog health
GET /health/watchdogs

# Get overall system health
GET /health
```

## Troubleshooting

### Worker Issues

**Worker not starting:**
- Check if worker type is enabled in configuration
- Verify Ray is initialized properly
- Check for import errors in logs

**Worker timing out:**
- Increase `WORKER_TASK_TIMEOUT`
- Check data provider availability
- Review network latency

**High failure rate:**
- Check data provider API keys
- Review error messages in metrics
- Verify Azure OpenAI configuration

### Watchdog Issues

**Watchdog not checking:**
- Verify watchdog is enabled in configuration
- Check if manager is started
- Review check interval settings

**Too many/few alerts:**
- Adjust threshold values
- Review check intervals
- Fine-tune detection logic

**Stale watchdog:**
- Check for errors in watchdog logs
- Verify data provider connectivity
- Restart specific watchdog via manager

## Performance Tuning

### Worker Optimization

- Adjust pool size based on CPU cores: `WORKER_POOL_SIZE = CPU_CORES * 2`
- Tune concurrency: `WORKER_MAX_CONCURRENT_TASKS = POOL_SIZE * 5`
- Set appropriate timeouts based on average task duration
- Enable only required workers to save resources

### Watchdog Optimization

- Balance check intervals with detection needs
- Disable unused watchdogs to reduce overhead
- Adjust thresholds to reduce false positives
- Use event persistence for critical events only

## Best Practices

1. **Always enable health monitoring in production**
2. **Start with conservative thresholds and tune based on data**
3. **Monitor circuit breaker states for worker recovery**
4. **Set up alerts for unhealthy components**
5. **Review metrics regularly to identify trends**
6. **Use feature flags to safely roll out changes**
7. **Keep event history for post-incident analysis**
8. **Document any custom threshold adjustments**

## Support

For issues or questions:
- Check logs for error details
- Review health metrics for anomalies
- Consult the main FIML documentation
- Open an issue on GitHub
