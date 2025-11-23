# Provider System

FIML uses an extensible provider system for data access.

## Base Provider Interface

All providers implement `BaseProvider`:

```python
class BaseProvider:
    async def fetch_price(self, symbol: str) -> float
    async def fetch_ohlcv(self, symbol: str, timeframe: str) -> list
    async def fetch_fundamentals(self, symbol: str) -> dict
```

## Implemented Providers

### Yahoo Finance
- Free tier
- Equity and ETF data
- Real-time quotes
- Historical data

### Alpha Vantage
- Premium equity data
- Fundamentals
- Technical indicators
- 5 requests/minute (free tier)

### Financial Modeling Prep (FMP)
- Financial statements
- Company profiles
- Market data
- 300 requests/minute

### CCXT
- Multi-exchange support
- Cryptocurrency data
- Real-time and historical
- 30+ exchanges

### Mock Provider
- Testing and development
- Predictable responses
- No external dependencies

## Adding a Provider

See [Contributing Guide](../development/contributing.md#adding-new-data-providers).
