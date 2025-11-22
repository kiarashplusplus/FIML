# Cache Optimization Guide

## Overview

FIML implements a sophisticated multi-layer caching system optimized for financial data with sub-100ms latency targets.

## Architecture

### L1 Cache (Redis)
- **Target Latency**: 10-100ms
- **Technology**: Redis in-memory cache
- **Use Case**: Ultra-fast access to frequently requested data
- **Features**:
  - Automatic TTL management
  - Pipeline batch operations
  - Connection pooling
  - Hit rate tracking

### L2 Cache (PostgreSQL + TimescaleDB)
- **Target Latency**: 300-700ms
- **Technology**: PostgreSQL with TimescaleDB extension
- **Use Case**: Persistent storage for historical and time-series data
- **Features**:
  - Time-series optimization
  - Automatic data retention
  - Complex query support

## Cache Optimization Features

### 1. Cache Warming

Proactively loads frequently accessed data to minimize cold-start latency.

**Configuration:**
```python
# In fiml.core.config
cache_warming_enabled = True
cache_warming_interval_seconds = 300  # 5 minutes
```

**Popular Symbols** (automatically warmed):
- **US Tech**: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA
- **Major Indices**: SPY, QQQ, DIA, IWM
- **Popular Stocks**: AMD, NFLX, DIS, INTC, PYPL, CRM, ADBE
- **Major Cryptos**: BTC, ETH, BNB, SOL, ADA

**Usage:**
```python
from fiml.cache import cache_warmer

# Warm cache on startup
await cache_warmer.warm_on_startup()

# Warm specific assets
assets = [...]  # List of Asset objects
result = await cache_warmer.warm_cache(assets=assets)

# Get warming statistics
stats = cache_warmer.get_stats()
```

### 2. Intelligent Eviction

Implements smart cache eviction policies to maximize hit rates.

**Supported Policies:**
- **LRU** (Least Recently Used) - Default
- **LFU** (Least Frequently Used)
- **TTL** (Time To Live)
- **FIFO** (First In First Out)

**Configuration:**
```python
# In fiml.core.config
cache_eviction_policy = "lru"  # or "lfu", "ttl", "fifo"
cache_max_tracked_entries = 10000
cache_memory_pressure_threshold = 0.9  # 90%
```

**Usage:**
```python
from fiml.cache import eviction_tracker, EvictionPolicy

# Track cache accesses
eviction_tracker.track_access("price:AAPL:yahoo")

# Get eviction candidates
candidates = eviction_tracker.get_eviction_candidates(count=10)

# Check memory pressure
should_evict = eviction_tracker.should_evict(
    current_size=9500, 
    max_size=10000
)

# Get statistics
stats = eviction_tracker.get_stats()
```

### 3. Performance Metrics

Comprehensive metrics tracking for cache performance monitoring.

**Metrics Collected:**
- **Latency**: p50, p95, p99 percentiles for L1 and L2
- **Hit Rates**: Separate tracking for L1 and L2 caches
- **Evictions**: Count and reasons for cache evictions
- **Throughput**: Requests per second
- **Memory**: Cache size and pressure

**Usage:**
```python
from fiml.cache import cache_manager

# Initialize cache manager
await cache_manager.initialize()

# Get comprehensive statistics
stats = await cache_manager.get_stats()

print(f"L1 Hit Rate: {stats['l1']['hit_rate_percent']}%")
print(f"L1 p95 Latency: {stats['l1']['p95_latency_ms']}ms")
print(f"L2 Hit Rate: {stats['l2']['hit_rate_percent']}%")
```

**Example Output:**
```json
{
  "l1": {
    "hits": 15234,
    "misses": 1256,
    "hit_rate_percent": 92.38,
    "avg_latency_ms": 15.42,
    "p50_latency_ms": 12.5,
    "p95_latency_ms": 35.8,
    "p99_latency_ms": 48.3
  },
  "l2": {
    "status": "initialized",
    "hits": 856,
    "misses": 400,
    "hit_rate_percent": 68.15,
    "avg_latency_ms": 425.3
  },
  "overall": {
    "total_requests": 16490,
    "l1_hit_rate": 92.38,
    "l2_hit_rate": 68.15
  }
}
```

## Performance Benchmarks

### Running Benchmarks

```bash
# Run all cache benchmarks
pytest benchmarks/bench_cache.py --benchmark-only --benchmark-verbose

# Save benchmark results
pytest benchmarks/bench_cache.py --benchmark-only --benchmark-autosave

# Compare with previous results
pytest benchmarks/bench_cache.py --benchmark-only --benchmark-compare
```

### Benchmark Tests

**L1 Cache Latency:**
- `test_l1_single_get_latency` - Single GET operation
- `test_l1_single_set_latency` - Single SET operation
- `test_l1_batch_get_latency` - Batch GET (100 keys)

**L2 Cache Latency:**
- `test_l2_initialization` - Connection setup

**Concurrent Performance:**
- `test_concurrent_l1_reads_100` - 100 concurrent reads
- `test_concurrent_l1_reads_1000` - 1000 concurrent reads

**Hit Rate Measurement:**
- `test_cache_hit_rate_measurement` - Mixed hits/misses
- `test_cache_stats_retrieval` - Statistics collection

### Expected Results

**L1 Cache (Redis):**
- GET latency: 10-50ms (local), 15-100ms (network)
- SET latency: 12-60ms (local), 20-120ms (network)
- Batch operations: 50-200ms for 100 keys
- 1000 concurrent reads: 200-500ms

**L2 Cache (PostgreSQL):**
- Query latency: 300-700ms
- Batch operations: 500-1500ms

## Testing

### Unit Tests

```bash
# Run unit tests without services
pytest tests/test_cache_improved.py -v

# Run integration tests (requires Redis/PostgreSQL)
pytest tests/test_cache_improved.py -v -m integration
```

### Integration Tests

```bash
# Start services
docker-compose up -d redis postgres

# Run cache tests
pytest tests/test_cache.py -v
pytest tests/test_cache_improved.py -v

# Measure actual latency
pytest tests/test_cache_improved.py::TestIntegrationWithServices -v -s
```

## Best Practices

### 1. Cache Warming Strategy

```python
# Warm cache on application startup
async def startup_event():
    await cache_manager.initialize()
    
    # Warm with popular symbols
    await cache_warmer.warm_on_startup()
    
    # Start scheduled warming (every 5 minutes)
    asyncio.create_task(
        cache_warmer.scheduled_warm(interval_seconds=300)
    )
```

### 2. Batch Operations

Always use batch operations for multiple keys:

```python
# Good - Batch operation
assets = [...]  # List of 100 assets
prices = await cache_manager.get_prices_batch(assets)

# Avoid - Individual operations in loop
prices = []
for asset in assets:
    price = await cache_manager.get_price(asset)
    prices.append(price)
```

### 3. TTL Configuration

Set appropriate TTLs based on data freshness requirements:

```python
# Price data - changes frequently
cache_ttl_price = 10  # 10 seconds

# Fundamentals - changes less often
cache_ttl_fundamentals = 3600  # 1 hour

# Macro data - changes rarely
cache_ttl_macro = 86400  # 24 hours
```

### 4. Monitoring

Regularly monitor cache performance:

```python
# Log cache statistics periodically
async def log_cache_stats():
    while True:
        stats = await cache_manager.get_stats()
        logger.info("Cache performance", **stats)
        await asyncio.sleep(60)  # Every minute
```

## Troubleshooting

### Low Hit Rate

**Symptoms**: Hit rate < 70%

**Solutions**:
1. Increase cache warming frequency
2. Add more popular symbols to warming list
3. Increase TTL for stable data
4. Review access patterns

### High Latency

**Symptoms**: L1 latency > 100ms

**Solutions**:
1. Check Redis connection pool size
2. Verify network latency to Redis
3. Use batch operations for multiple keys
4. Check Redis memory usage

### Memory Pressure

**Symptoms**: Frequent evictions, OOM errors

**Solutions**:
1. Adjust eviction policy (use LFU for better hit rate)
2. Reduce TTLs for less important data
3. Increase Redis memory limit
4. Reduce `cache_max_tracked_entries`

## Configuration Reference

```python
# fiml.core.config.Settings

# Cache warming
cache_warming_enabled: bool = True
cache_warming_interval_seconds: int = 300

# Eviction
cache_eviction_policy: Literal["lru", "lfu", "ttl", "fifo"] = "lru"
cache_max_tracked_entries: int = 10000
cache_memory_pressure_threshold: float = 0.9

# TTLs (seconds)
cache_ttl_price: int = 10
cache_ttl_fundamentals: int = 3600
cache_ttl_technical: int = 300
cache_ttl_news: int = 600
cache_ttl_macro: int = 86400

# Redis
redis_host: str = "localhost"
redis_port: int = 6379
redis_max_connections: int = 50
redis_socket_timeout: int = 5

# PostgreSQL
postgres_pool_size: int = 20
postgres_max_overflow: int = 10
```

## API Reference

### CacheManager

```python
class CacheManager:
    async def initialize() -> None
    async def shutdown() -> None
    async def get(key: str) -> Optional[Any]
    async def set(key: str, value: Any, ttl_seconds: Optional[int]) -> bool
    async def get_prices_batch(assets: List[Asset]) -> List[Optional[Dict]]
    async def set_prices_batch(items: List[tuple]) -> int
    async def get_stats() -> Dict[str, Any]
```

### CacheWarmer

```python
class CacheWarmer:
    async def warm_cache(assets: Optional[List[Asset]], force: bool) -> Dict
    async def warm_on_startup() -> Dict
    async def scheduled_warm(interval_seconds: int) -> None
    def get_stats() -> Dict
```

### EvictionTracker

```python
class EvictionTracker:
    def track_access(key: str) -> None
    def should_evict(current_size: int, max_size: int) -> bool
    def get_eviction_candidates(count: int) -> List[str]
    def get_stats() -> Dict
```

## Future Enhancements

1. **Predictive Caching**: Use ML to predict which data will be accessed
2. **Geographic Distribution**: Multi-region cache replication
3. **Adaptive TTLs**: Automatically adjust TTLs based on access patterns
4. **Cache Compression**: Reduce memory usage with compression
5. **Tiered Storage**: Add L3 cache with object storage (S3)

## References

- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [TimescaleDB Performance Tuning](https://docs.timescale.com/timescaledb/latest/how-to-guides/configuration/)
- [Cache Eviction Algorithms](https://en.wikipedia.org/wiki/Cache_replacement_policies)
