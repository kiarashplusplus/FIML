# Phase 2 Setup Guide: Provider Integration & Real Data Fetching

This guide explains how to set up and use the Phase 2 features of FIML, including new data providers and the compliance framework.

## Overview

Phase 2 adds:
- **3 New Data Providers**: Alpha Vantage, FMP (Financial Modeling Prep), and CCXT (crypto)
- **Real Data Fetching**: MCP tools now fetch actual market data instead of returning mocks
- **Compliance Framework**: Regional compliance checks and disclaimers
- **Intelligent Provider Selection**: Automatic provider selection based on availability and performance

## Prerequisites

- Python 3.11+
- API keys for data providers (see below)
- Redis and PostgreSQL (for caching, optional but recommended)

## Getting API Keys

### Alpha Vantage (Free Tier)

1. Visit https://www.alphavantage.co/support/#api-key
2. Sign up for a free API key
3. **Limits**: 5 requests/minute, 500 requests/day
4. **Provides**: Stock prices, OHLCV data, fundamentals

### FMP - Financial Modeling Prep (Free Tier)

1. Visit https://financialmodelingprep.com/developer/docs/
2. Create account and get API key
3. **Limits**: 250 requests/day (free tier)
4. **Provides**: Real-time prices, financial statements, company profiles

### CCXT - Cryptocurrency Data (No API Key Needed)

- **No registration required** for read-only public data
- Supports 100+ exchanges (Binance, Coinbase, Kraken, etc.)
- **Provides**: Real-time crypto prices, OHLCV data, order books

## Configuration

### 1. Set Environment Variables

Edit your `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit with your API keys
nano .env
```

Add your API keys:

```bash
# Alpha Vantage
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here

# FMP
FMP_API_KEY=your_fmp_key_here

# CCXT - No key needed for public data
# Optional: Add exchange API keys for private data/trading
BINANCE_API_KEY=
BINANCE_SECRET_KEY=

# Compliance Settings
DEFAULT_REGION=US
ENABLE_COMPLIANCE_CHECKS=true
```

### 2. Install Dependencies

```bash
# Install FIML with all dependencies
pip install -e ".[dev]"

# Or install specific provider dependencies
pip install alpha-vantage ccxt aiohttp
```

### 3. Verify Installation

```bash
# Run tests to verify providers work
pytest tests/test_phase2_providers.py -v

# Or test manually in Python
python
>>> from fiml.providers.alpha_vantage import AlphaVantageProvider
>>> provider = AlphaVantageProvider("your_key")
>>> # Provider created successfully
```

## Usage

### Using the MCP Tools

The MCP tools now fetch real data automatically:

#### Search By Symbol (Equity)

```json
{
  "name": "search-by-symbol",
  "arguments": {
    "symbol": "AAPL",
    "market": "US",
    "depth": "standard",
    "language": "en"
  }
}
```

**What Happens:**
1. Compliance check runs (detects advice requests, applies regional rules)
2. Arbitration engine selects best provider (Yahoo Finance, Alpha Vantage, or FMP)
3. Real price data fetched from provider
4. Regional disclaimer added
5. Response returned with data lineage showing which provider was used

#### Search By Coin (Cryptocurrency)

```json
{
  "name": "search-by-coin",
  "arguments": {
    "symbol": "BTC",
    "exchange": "binance",
    "pair": "USDT",
    "depth": "standard",
    "language": "en"
  }
}
```

**What Happens:**
1. Compliance check runs (crypto-specific warnings)
2. CCXT provider selected for specified exchange
3. Real-time crypto data fetched
4. Crypto-specific disclaimer added
5. Response includes exchange info and crypto metrics

### Provider Selection Logic

The system automatically selects providers based on:

1. **Availability**: Does the provider have an API key configured?
2. **Asset Support**: Does the provider support this asset type?
3. **Health**: Is the provider currently healthy?
4. **Performance**: Provider scoring based on:
   - Freshness (30% weight)
   - Latency (25% weight)
   - Uptime (20% weight)
   - Completeness (15% weight)
   - Reliability (10% weight)

**Priority Order (for equities):**
1. Alpha Vantage (if API key available) - Priority 7
2. FMP (if API key available) - Priority 6
3. Yahoo Finance (always available) - Priority 5
4. Mock Provider (testing only) - Priority 1

**For Cryptocurrency:**
- CCXT with selected exchange - Priority 8

### Compliance Framework

All responses now include compliance checks:

#### Advice Detection

The system detects and blocks investment advice requests:

```python
# Blocked queries (compliance failure):
"Should I buy AAPL?"
"Is BTC a good investment?"
"Tell me what to invest in"

# Allowed queries (information only):
"What's the price of AAPL?"
"Show me BTC data"
"Compare TSLA and F"
```

#### Regional Disclaimers

Disclaimers are automatically generated based on region:

- **US**: SEC/FINRA compliant disclaimers
- **EU**: MiFID II and GDPR notices
- **UK**: FCA compliant warnings
- **JP**: Bilingual Japanese/English
- **Global**: General financial information disclaimers

#### Asset-Specific Warnings

Different asset types get different warnings:

- **Equities**: Standard investment risk warnings
- **Crypto**: High volatility and loss warnings
- **Derivatives**: Leverage and loss exceeding investment warnings

## Monitoring and Debugging

### Check Provider Status

```python
from fiml.providers.registry import provider_registry

# Initialize registry
await provider_registry.initialize()

# Check what providers are registered
print(provider_registry.providers.keys())

# Get health status
for name, provider in provider_registry.providers.items():
    health = await provider.health_check()
    print(f"{name}: {'healthy' if health.is_healthy else 'unhealthy'}")
```

### View Data Lineage

Every response includes `data_lineage` showing:
- Which providers were used
- Arbitration score
- Whether conflicts were resolved
- Source count

```json
{
  "data_lineage": {
    "providers": ["alpha_vantage"],
    "arbitration_score": 95.0,
    "conflict_resolved": false,
    "source_count": 1
  }
}
```

### Rate Limit Handling

Providers automatically handle rate limits:

- **Alpha Vantage**: 5 req/min, auto-waits if exceeded
- **FMP**: 10 req/min (conservative), auto-retries
- **CCXT**: Exchange-specific limits, handled by ccxt library

Rate limit errors include `retry_after` time in seconds.

## Troubleshooting

### Provider Not Initializing

```bash
# Check if API key is set
echo $ALPHA_VANTAGE_API_KEY

# Check logs for initialization errors
grep "provider" logs/fiml.log

# Test provider directly
python -c "from fiml.providers.alpha_vantage import AlphaVantageProvider; import asyncio; asyncio.run(AlphaVantageProvider('test').initialize())"
```

### No Data Returned

1. **Check API key is valid**
2. **Check rate limits** - wait 60 seconds and try again
3. **Check symbol format** - Use correct exchange format (e.g., `AAPL` not `AAPL.US`)
4. **Check logs** for specific error messages

### Compliance Errors

If you receive compliance errors:

1. **Check query wording** - Avoid words like "should I", "recommend", "advise"
2. **Check region settings** - Some features may be restricted in certain regions
3. **Check asset type** - High-risk assets may have additional restrictions

## Advanced Configuration

### Custom Provider Priority

Edit `fiml/providers/registry.py` to change provider priority:

```python
# Higher priority = selected first
AlphaVantageProvider(priority=10)  # Highest priority
FMPProvider(priority=8)
YahooFinanceProvider(priority=5)
```

### Custom Compliance Rules

Add regional rules in `fiml/compliance/router.py`:

```python
ComplianceRule(
    rule_id="CUSTOM-001",
    region=Region.US,
    rule_type="warning",
    description="Custom warning message",
    severity="high"
)
```

### Disable Specific Providers

Set in `.env`:

```bash
# Disable crypto
ENABLE_CRYPTO=false

# Disable specific features
ENABLE_DERIVATIVES=false
ENABLE_INTERNATIONAL_MARKETS=false
```

## API Reference

### Provider Methods

All providers implement these methods:

```python
# Initialize provider
await provider.initialize()

# Fetch price data
response = await provider.fetch_price(asset)

# Fetch OHLCV data
response = await provider.fetch_ohlcv(asset, timeframe="1d", limit=100)

# Fetch fundamentals
response = await provider.fetch_fundamentals(asset)

# Health check
health = await provider.health_check()

# Shutdown
await provider.shutdown()
```

### Compliance Methods

```python
from fiml.compliance.router import compliance_router
from fiml.compliance.disclaimers import disclaimer_generator

# Check compliance
result = await compliance_router.check_compliance(
    request_type="price_query",
    asset_type="equity",
    region=Region.US,
    user_query="What's the price?"
)

# Generate disclaimer
disclaimer = disclaimer_generator.generate(
    asset_class=AssetClass.EQUITY,
    region=Region.US
)

# Get risk warning
warning = disclaimer_generator.get_risk_warning(AssetClass.CRYPTO)
```

## Performance Tuning

### Cache Configuration

Enable caching to reduce API calls:

```bash
# In .env
ENABLE_PREDICTIVE_CACHE=true

# Redis settings
REDIS_HOST=localhost
REDIS_PORT=6379

# Cache TTL (in seconds)
CACHE_TTL_PRICE=300      # 5 minutes for prices
CACHE_TTL_FUNDAMENTALS=86400  # 24 hours for fundamentals
```

### Rate Limit Optimization

```bash
# Increase limits if you have premium API keys
ALPHA_VANTAGE_RATE_LIMIT=75  # Premium tier
FMP_RATE_LIMIT=300           # Premium tier
```

## Next Steps

- Explore the [ARCHITECTURE.md](../architecture/overview.md) for system design details
- Read [BLUEPRINT.md](blueprint.md) for the 10-year vision
- Check [CONTRIBUTING.md](../development/contributing.md) to contribute
- Review test files in `tests/` for usage examples

## Support

For issues or questions:
1. Check existing issues: https://github.com/kiarashplusplus/FIML/issues
2. Create new issue with details about your setup
3. Include logs and error messages

## License

Apache 2.0 License - see LICENSE file for details
