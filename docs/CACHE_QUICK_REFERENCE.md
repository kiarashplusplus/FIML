# Cache Optimizations - Quick Reference

## 🚀 Quick Start

### 1. Import Components
```python
from fiml.cache import (
    cache_manager,
    PredictiveCacheWarmer,
    BatchUpdateScheduler,
    cache_analytics,
    EvictionPolicy
)
```

### 2. Initialize Cache Warming
```python
warmer = PredictiveCacheWarmer(
    cache_manager=cache_manager,
    provider_registry=provider_registry,
    warming_schedule=[0, 6, 12, 18],  # Every 6 hours
    max_symbols_per_batch=50
)

await warmer.start_background_warming(interval_minutes=60)
```

### 3. Enable Batch Scheduling
```python
scheduler = BatchUpdateScheduler(
    cache_manager=cache_manager,
    provider_registry=provider_registry,
    batch_size=50,
    batch_interval_seconds=60
)

await scheduler.start()
```

### 4. Monitor Performance
```python
# Get comprehensive report
report = cache_analytics.get_comprehensive_report()

print(f"Hit Rate: {report['overall']['hit_rate_percent']}%")
print(f"Recommendations: {report['recommendations']}")
```

## 📊 Common Operations

### Cache Warming

```python
# Record access patterns
warmer.record_cache_access("AAPL", DataType.PRICE)

# Add market events
warmer.add_market_event("TSLA", "earnings")

# Manual warming cycle
await warmer.run_warming_cycle()

# Check stats
stats = warmer.get_warming_stats()
```

### Batch Updates

```python
# Schedule single update
await scheduler.schedule_update(
    asset=Asset(symbol="AAPL", asset_type="equity"),
    data_type=DataType.PRICE,
    provider="yahoo",
    priority=5
)

# Schedule batch
updates = [(asset, DataType.PRICE, "yahoo", 0) for asset in assets]
await scheduler.schedule_updates_batch(updates)

# Force flush
await scheduler.flush_pending()
```

### Analytics

```python
# Record access
cache_analytics.record_cache_access(
    DataType.PRICE,
    is_hit=True,
    latency_ms=12.0,
    cache_level="l1"
)

# Detect pollution
pollution = cache_analytics.detect_cache_pollution()
if pollution['is_polluted']:
    print(f"⚠️ Pollution: {pollution['pollution_score_percent']}%")

# Get trends
trends = cache_analytics.get_hourly_trends(hours=24)
```

### Eviction Control

```python
from fiml.cache import L1Cache, EvictionPolicy

# Initialize with policy
cache = L1Cache(eviction_policy=EvictionPolicy.LFU)

# Protect keys
cache.protect_key("critical:AAPL:price")

# Manual eviction
evicted = await cache.evict_least_used(count=10)

# Check stats
stats = cache.get_eviction_stats()
access_stats = cache.get_access_stats()
```

### Dynamic TTL

```python
# Automatic based on asset and market
await cache_manager.set_price(asset, provider, price_data)

# Read-through pattern
data = await cache_manager.get_with_read_through(
    key="price:AAPL:yahoo",
    data_type=DataType.PRICE,
    fetch_fn=lambda: provider.get_price(asset),
    asset=asset
)
```

## ⚙️ Configuration

### Environment Variables

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_MAX_CONNECTIONS=50

# Base TTL (seconds)
CACHE_TTL_PRICE=300          # 5 min
CACHE_TTL_FUNDAMENTALS=86400 # 24h
CACHE_TTL_NEWS=600           # 10 min

# Warming
CACHE_WARMING_ENABLED=true
CACHE_WARMING_SCHEDULE="0,6,12,18"
CACHE_WARMING_BATCH_SIZE=50

# Batching
CACHE_BATCH_ENABLED=true
CACHE_BATCH_SIZE=50
CACHE_BATCH_INTERVAL=60
```

### Code Configuration

```python
# Cache Manager
cache_manager.market_open = time(9, 30)
cache_manager.market_close = time(16, 0)

# Warmer
warmer.min_request_threshold = 10
warmer.warming_schedule = [0, 6, 12, 18]

# Scheduler
scheduler.low_load_hours = list(range(0, 7))
scheduler.batch_size = 50

# L1 Cache
cache = L1Cache(
    eviction_policy=EvictionPolicy.HYBRID,
    protected_patterns=["critical:*", "price:AAPL*"]
)
```

## 🎯 Best Practices

### 1. Enable Warming for Production
```python
# Start warming early
await warmer.start_background_warming()

# Record accesses consistently
for symbol in frequently_accessed:
    warmer.record_cache_access(symbol, DataType.PRICE)
```

### 2. Use Batch Operations
```python
# Good: Batch operation
prices = await cache_manager.get_prices_batch(assets)

# Avoid: Loop of individual calls
# for asset in assets:
#     price = await cache_manager.get_price(asset)
```

### 3. Monitor and Act on Analytics
```python
# Daily health check
report = cache_analytics.get_comprehensive_report()

for rec in report['recommendations']:
    logger.warning(f"Cache optimization: {rec}")

# Check pollution
if report['pollution']['is_polluted']:
    # Adjust TTL or eviction policy
    pass
```

### 4. Protect Critical Data
```python
# Protect frequently accessed keys
cache_manager.l1.protect_key("price:SPY:yahoo")
cache_manager.l1.protect_key("price:QQQ:yahoo")

# Or use patterns
cache = L1Cache(protected_patterns=["price:INDEX:*"])
```

### 5. Choose Right Eviction Policy
```python
# Stable workload: LFU
cache = L1Cache(eviction_policy=EvictionPolicy.LFU)

# Mixed workload: Hybrid
cache = L1Cache(eviction_policy=EvictionPolicy.HYBRID)

# Temporal patterns: LRU (default)
cache = L1Cache(eviction_policy=EvictionPolicy.LRU)
```

## 🔍 Troubleshooting

### Low Hit Rate (<70%)

```python
# Check analytics
report = cache_analytics.get_comprehensive_report()

# Enable warming
await warmer.start_background_warming()

# Increase cache size
# Edit redis.conf: maxmemory 2gb

# Check TTL
for data_type in DataType:
    ttl = cache_manager._get_ttl(data_type)
    print(f"{data_type}: {ttl}s")
```

### High Latency

```python
# Check percentiles
stats = cache_analytics.get_data_type_stats()
for data_type, metrics in stats.items():
    print(f"{data_type} p99: {metrics['latency_ms']['p99']}ms")

# Use batch operations
prices = await cache_manager.get_prices_batch(assets)

# Check Redis connection pool
# Increase REDIS_MAX_CONNECTIONS
```

### Cache Pollution

```python
# Detect pollution
pollution = cache_analytics.detect_cache_pollution()

if pollution['is_polluted']:
    # Switch to LFU
    cache = L1Cache(eviction_policy=EvictionPolicy.LFU)
    
    # Reduce TTL
    CACHE_TTL_PRICE = 180  # 3 min instead of 5
```

### Too Many API Calls

```python
# Enable batch scheduler
await scheduler.start()

# Schedule instead of immediate fetch
await scheduler.schedule_update(asset, DataType.PRICE, provider)

# Check savings
stats = scheduler.get_stats()
print(f"API calls saved: {stats['api_calls_saved']}")
```

## 📈 Monitoring Commands

```python
# Overall stats
stats = cache_manager.get_stats()
print(f"L1 hit rate: {stats['l1']['hit_rate_percent']}%")

# Warming effectiveness
warming_stats = warmer.get_warming_stats()
print(f"Success rate: {warming_stats['success_rate_percent']}%")

# Batch efficiency
batch_stats = scheduler.get_stats()
print(f"API reduction: {batch_stats['api_calls_saved']}")

# Analytics summary
report = cache_analytics.get_comprehensive_report()
print(report['recommendations'])
```

## 🧪 Testing

```bash
# Run tests
pytest tests/test_cache_optimizations.py -v

# Run benchmarks
python benchmarks/bench_cache_optimizations.py

# Specific benchmark
pytest benchmarks/bench_cache_optimizations.py::test_comprehensive_benchmark -v
```

## 📚 Documentation

- **Full Guide:** `docs/CACHE_ENHANCEMENTS.md`
- **Architecture:** `docs/CACHE_ARCHITECTURE.md`
- **Summary:** `CACHE_ENHANCEMENTS_SUMMARY.md`
- **Blueprint:** `BLUEPRINT.md` Section 7

## 🎓 Examples

### Complete Setup

```python
async def setup_optimized_cache():
    # Initialize cache manager
    await cache_manager.initialize()
    
    # Setup warming
    warmer = PredictiveCacheWarmer(
        cache_manager=cache_manager,
        provider_registry=provider_registry
    )
    await warmer.start_background_warming()
    
    # Setup batching
    scheduler = BatchUpdateScheduler(
        cache_manager=cache_manager,
        provider_registry=provider_registry
    )
    await scheduler.start()
    
    return cache_manager, warmer, scheduler

# Use it
cache_mgr, warmer, scheduler = await setup_optimized_cache()
```

### Monitoring Loop

```python
async def monitor_cache_health():
    while True:
        # Get report
        report = cache_analytics.get_comprehensive_report()
        
        # Log metrics
        logger.info(
            "Cache health",
            hit_rate=report['overall']['hit_rate_percent'],
            recommendations=len(report['recommendations'])
        )
        
        # Check thresholds
        if report['overall']['hit_rate_percent'] < 70:
            logger.warning("Low hit rate detected!")
            
        await asyncio.sleep(300)  # Every 5 minutes
```

## 🚨 Alerts

### Prometheus Alert Rules

```yaml
# Hit rate too low
- alert: CacheHitRateLow
  expr: fiml_cache_hit_rate{data_type="price"} < 70
  for: 5m
  annotations:
    summary: "Cache hit rate below 70%"

# High latency
- alert: CacheLatencyHigh
  expr: histogram_quantile(0.95, fiml_cache_latency_seconds) > 0.1
  for: 5m
  annotations:
    summary: "p95 cache latency above 100ms"
```

## 💡 Pro Tips

1. **Start warming early** - Let it learn patterns for 24h before production
2. **Use batch ops everywhere** - 40% fewer API calls
3. **Monitor daily** - Check analytics recommendations
4. **Protect hot keys** - Prevent eviction of critical data
5. **Tune TTL dynamically** - Based on your data update frequency
6. **Use read-through** - Simplifies cache miss handling
7. **Profile regularly** - Run benchmarks quarterly
8. **Export to Prometheus** - Historical trend analysis
