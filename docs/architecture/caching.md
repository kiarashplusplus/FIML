# Caching Strategy

FIML implements a two-tier caching architecture for optimal performance.

## L1 Cache - Redis

**Target Latency**: 10-100ms

- In-memory key-value store
- Default TTL: 5 minutes
- LRU eviction policy
- Hot data storage

## L2 Cache - PostgreSQL + TimescaleDB

**Target Latency**: 300-700ms

- Persistent storage
- Default TTL: 1 hour
- Time-series optimization
- Historical data

## Cache Warming

Proactively populate cache for popular symbols:

```bash
CACHE_WARMING_ENABLED=true
CACHE_WARMING_SYMBOLS=AAPL,GOOGL,MSFT,TSLA,BTC,ETH
CACHE_WARMING_INTERVAL=600  # 10 minutes
```

## Cache Key Design

Keys include:
- Provider name
- Symbol
- Data type
- Parameters hash

Example: `yahoo:AAPL:price:standard`
