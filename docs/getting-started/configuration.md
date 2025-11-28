# Configuration

This guide covers all configuration options available in FIML.

## Environment Variables

FIML uses environment variables for configuration. The `.env` file contains all configurable options.

### Core Settings

```bash
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_WORKERS=4
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=production  # or development, staging
```

### Database Configuration

#### PostgreSQL

```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=fiml
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=fiml
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

#### Redis Cache

```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50
```

### Data Provider API Keys

#### Alpha Vantage

```bash
ALPHA_VANTAGE_API_KEY=your_key_here
ALPHA_VANTAGE_RATE_LIMIT=5  # Requests per minute
```

Get your free API key at [Alpha Vantage](https://www.alphavantage.co/support/#api-key).

#### Financial Modeling Prep (FMP)

```bash
FMP_API_KEY=your_key_here
FMP_RATE_LIMIT=300  # Requests per minute
```

Sign up at [FMP](https://site.financialmodelingprep.com/developer/docs).

#### CCXT (Cryptocurrency Exchanges)

```bash
CCXT_EXCHANGE=binance  # or coinbase, kraken, etc.
CCXT_API_KEY=your_key_here
CCXT_API_SECRET=your_secret_here
```

### Cache Configuration

#### L1 Cache (Redis)

```bash
CACHE_L1_ENABLED=true
CACHE_L1_TTL=300  # 5 minutes in seconds
CACHE_L1_MAX_SIZE=10000  # Maximum number of entries
```

#### L2 Cache (PostgreSQL)

```bash
CACHE_L2_ENABLED=true
CACHE_L2_TTL=3600  # 1 hour in seconds
CACHE_L2_MAX_SIZE=100000  # Maximum number of entries
```

#### Cache Warming

```bash
CACHE_WARMING_ENABLED=true
CACHE_WARMING_SYMBOLS=AAPL,GOOGL,MSFT,TSLA,BTC,ETH
CACHE_WARMING_INTERVAL=600  # 10 minutes
```

### Data Arbitration

Configure how the arbitration engine selects data providers:

```bash
# Scoring weights (must sum to 1.0)
ARBITRATION_WEIGHT_AVAILABILITY=0.3
ARBITRATION_WEIGHT_FRESHNESS=0.25
ARBITRATION_WEIGHT_RELIABILITY=0.25
ARBITRATION_WEIGHT_LATENCY=0.15
ARBITRATION_WEIGHT_COST=0.05

# Provider priority (comma-separated list)
ARBITRATION_PROVIDER_PRIORITY=alpha_vantage,fmp,yahoo,ccxt,mock

# Fallback behavior
ARBITRATION_ENABLE_FALLBACK=true
ARBITRATION_MAX_RETRIES=3
```

### Rate Limiting

```bash
# Global rate limits
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=300
RATE_LIMIT_BURST=50

# Per-endpoint rate limits
RATE_LIMIT_SEARCH_SYMBOL=60
RATE_LIMIT_SEARCH_COIN=60
RATE_LIMIT_FK_DSL=30
```

### WebSocket Configuration

```bash
# WebSocket settings
WEBSOCKET_MAX_CONNECTIONS=1000
WEBSOCKET_MAX_SUBSCRIPTIONS_PER_CONNECTION=50
WEBSOCKET_HEARTBEAT_INTERVAL=30  # seconds
WEBSOCKET_RECONNECT_DELAY=5  # seconds
```

### Compliance & Security

```bash
# Compliance settings
COMPLIANCE_ENABLED=true
COMPLIANCE_DEFAULT_REGION=US
COMPLIANCE_SUPPORTED_REGIONS=US,EU,UK,JP,AU,CA,SG,HK

# Security
ENABLE_CORS=true
CORS_ORIGINS=http://localhost:3000,https://yourapp.com
API_KEY_REQUIRED=false  # Set to true for production
```

### Monitoring & Logging

```bash
# Prometheus metrics
METRICS_ENABLED=true
METRICS_PORT=8000
METRICS_PATH=/metrics

# Structured logging
LOG_FORMAT=json  # or text
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_OUTPUT=stdout  # or file path

# Sentry error tracking (optional)
SENTRY_DSN=your_sentry_dsn
SENTRY_ENVIRONMENT=production
```

### Ray Multi-Agent Framework

```bash
# Ray cluster configuration
RAY_ENABLED=true
RAY_ADDRESS=auto  # or ray://host:port
RAY_NUM_CPUS=4
RAY_NUM_GPUS=0
RAY_MEMORY=8GB
```

### Kafka Event Streaming

```bash
# Kafka configuration (optional)
KAFKA_ENABLED=false
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_PREFIX=fiml
```

## Configuration Files

### pyproject.toml

Project metadata and dependencies are defined in `pyproject.toml`:

```toml
[project]
name = "fiml"
version = "0.4.1"
description = "Financial Intelligence Meta-Layer"
requires-python = ">=3.11"
```

### docker-compose.yml

Service orchestration is defined in `docker-compose.yml`. You can customize:

- Service resource limits
- Volume mounts
- Network configuration
- Port mappings

Example customization:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

## Configuration Profiles

### Development

For local development:

```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
CACHE_L1_TTL=60
CACHE_L2_TTL=300
METRICS_ENABLED=false
```

### Staging

For staging environment:

```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
CACHE_L1_TTL=300
CACHE_L2_TTL=3600
METRICS_ENABLED=true
API_KEY_REQUIRED=true
```

### Production

For production deployment:

```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
CACHE_L1_TTL=600
CACHE_L2_TTL=7200
METRICS_ENABLED=true
API_KEY_REQUIRED=true
SENTRY_DSN=your_sentry_dsn
```

## Advanced Configuration

### Custom Provider Configuration

You can add custom data providers by extending the provider system. See [Provider System](../architecture/providers.md) for details.

### Custom Caching Strategy

Customize cache behavior programmatically:

```python
from fiml.cache import CacheConfig

cache_config = CacheConfig(
    l1_ttl=300,
    l2_ttl=3600,
    eviction_policy="LRU",
    max_memory_mb=1024
)
```

### Custom Arbitration Scoring

Modify arbitration scoring logic:

```python
from fiml.arbitration import ArbitrationConfig

arbitration_config = ArbitrationConfig(
    weights={
        "availability": 0.3,
        "freshness": 0.25,
        "reliability": 0.25,
        "latency": 0.15,
        "cost": 0.05
    },
    min_score_threshold=0.5
)
```

## Configuration Validation

FIML validates configuration on startup. Check logs for any issues:

```bash
docker-compose logs api | grep -i "config"
```

Or use the validation endpoint:

```bash
curl http://localhost:8000/config/validate
```

## Best Practices

1. **Never commit secrets**: Use `.env` files locally and environment variables in production
2. **Use strong passwords**: Especially for production databases
3. **Enable rate limiting**: Protect against abuse
4. **Configure monitoring**: Set up Prometheus and Grafana for production
5. **Set appropriate TTLs**: Balance freshness vs. API costs
6. **Test configuration**: Always validate before deploying

## Next Steps

- [Quick Start Guide](quickstart.md) - Start using FIML
- [Architecture Overview](../architecture/overview.md) - Understand the system
- [Deployment Guide](../development/deployment.md) - Deploy to production
