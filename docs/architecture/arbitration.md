# Data Arbitration

The arbitration engine intelligently selects data providers based on multiple scoring factors.

## Scoring Factors

### Availability (30%)

Provider uptime and current health status.

### Freshness (25%)

How recent the data is from each provider.

### Reliability (25%)

Historical accuracy and consistency.

### Latency (15%)

Response time and performance.

### Cost (5%)

API rate limits and pricing considerations.

## Fallback Strategy

When a provider fails:

1. Score remaining providers
2. Select next best option
3. Retry with exponential backoff
4. Cache fallback decisions

## Configuration

Customize scoring weights in `.env`:

```bash
ARBITRATION_WEIGHT_AVAILABILITY=0.3
ARBITRATION_WEIGHT_FRESHNESS=0.25
ARBITRATION_WEIGHT_RELIABILITY=0.25
ARBITRATION_WEIGHT_LATENCY=0.15
ARBITRATION_WEIGHT_COST=0.05
```
