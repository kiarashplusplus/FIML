# Data Provider Overview

FIML supports 16 data providers across multiple asset classes and data types. This document provides an overview of each provider, their capabilities, and configuration requirements.

## Provider Summary Table

| Provider | Asset Types | Real-time | Historical | Fundamentals | News | API Key Required |
|----------|-------------|-----------|------------|--------------|------|------------------|
| **Yahoo Finance** | Stocks, ETFs, Indices | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Alpha Vantage** | Stocks, Forex | ✅ | ✅ | ✅ | ✅ | ✅ |
| **FMP** | Stocks | ✅ | ✅ | ✅ | ❌ | ✅ |
| **CCXT** | Crypto | ✅ | ✅ | ❌ | ❌ | ❌ (for public data) |
| **NewsAPI** | N/A | N/A | N/A | N/A | ✅ | ✅ |
| **Polygon.io** | Stocks, Options, Crypto, Forex | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Finnhub** | Stocks, Forex, Crypto | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Twelvedata** | Stocks, Forex, ETF, Crypto | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Tiingo** | Stocks, ETF, Crypto | ✅ | ✅ | Limited | ✅ | ✅ |
| **Intrinio** | Stocks, Options, ETF | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Marketstack** | Stocks, Indices, ETF | ✅ | ✅ | Limited | ❌ | ✅ |
| **CoinGecko** | Crypto | ✅ | ✅ | ✅ | ❌ | ❌ |
| **CoinMarketCap** | Crypto | ✅ | Limited | ✅ | ❌ | ✅ |
| **Quandl** | Stocks, Commodities, Economics | ❌ | ✅ | Limited | ❌ | ✅ |
| **Mock Provider** | All | ✅ | ✅ | ✅ | ✅ | ❌ |

## Provider Details

### 1. Yahoo Finance
- **Type**: Free, no API key required
- **Coverage**: US and global equities, ETFs, indices
- **Best for**: General market data, hobbyist projects
- **Rate Limits**: Very permissive (2000 calls/min)
- **Data Quality**: Good for end-of-day, decent for real-time
- **Config**: No configuration needed

### 2. Alpha Vantage
- **Type**: Freemium (API key required)
- **Coverage**: US equities, forex, technical indicators
- **Best for**: Technical analysis, fundamental data
- **Rate Limits**: Free tier - 5 calls/min, 500/day
- **Data Quality**: High quality, well-documented
- **Config**: `ALPHA_VANTAGE_API_KEY`

### 3. FMP (Financial Modeling Prep)
- **Type**: Freemium (API key required)
- **Coverage**: US equities, fundamentals
- **Best for**: Financial modeling, fundamental analysis
- **Rate Limits**: 250 calls/day (free tier)
- **Data Quality**: Excellent fundamentals
- **Config**: `FMP_API_KEY`

### 4. CCXT (Crypto Exchange Integration)
- **Type**: Free for public data
- **Coverage**: Multi-exchange cryptocurrency data
- **Best for**: Cryptocurrency trading, arbitrage
- **Rate Limits**: Varies by exchange
- **Data Quality**: Real-time exchange data
- **Config**: Optional exchange-specific API keys

### 5. NewsAPI
- **Type**: Freemium (API key required)
- **Coverage**: Global news sources
- **Best for**: Market sentiment, news aggregation
- **Rate Limits**: Free tier - 100 requests/day
- **Data Quality**: Curated news from 80,000+ sources
- **Config**: `NEWSAPI_API_KEY` or `NEWSAPI_KEY`

### 6. Polygon.io ⭐ NEW
- **Type**: Freemium (API key required)
- **Coverage**: US stocks, options, crypto, forex
- **Best for**: Low-latency real-time data, tick-level data
- **Rate Limits**: 60 calls/min (varies by plan)
- **Data Quality**: Institutional-grade, low-latency
- **Config**: `POLYGON_API_KEY`
- **Priority**: 8 (highest among paid providers)

### 7. Finnhub ⭐ NEW
- **Type**: Freemium (API key required)
- **Coverage**: Global stocks, forex, crypto, fundamentals
- **Best for**: Global market coverage, economic indicators
- **Rate Limits**: 60 calls/min (free tier)
- **Data Quality**: Comprehensive global data
- **Config**: `FINNHUB_API_KEY`
- **Priority**: 7

### 8. Twelvedata ⭐ NEW
- **Type**: Freemium (API key required)
- **Coverage**: 100,000+ symbols - stocks, forex, ETF, crypto
- **Best for**: Global coverage, WebSocket streaming
- **Rate Limits**: 8 calls/min (free tier)
- **Data Quality**: 99.95% uptime, low latency
- **Config**: `TWELVEDATA_API_KEY`
- **Priority**: 7

### 9. Tiingo ⭐ NEW
- **Type**: Freemium (API key required)
- **Coverage**: EOD stocks, IEX real-time, news, crypto
- **Best for**: Quality EOD data, proprietary enrichment
- **Rate Limits**: 60 calls/min (varies by plan)
- **Data Quality**: High accuracy, data cleaning
- **Config**: `TIINGO_API_KEY`
- **Priority**: 7

### 10. Intrinio ⭐ NEW
- **Type**: Premium (API key required)
- **Coverage**: US stocks, options, fundamentals, ESG
- **Best for**: Options data, analyst estimates, compliance
- **Rate Limits**: 60 calls/min (varies by plan)
- **Data Quality**: Professional-grade, standardized
- **Config**: `INTRINIO_API_KEY`
- **Priority**: 7

### 11. Marketstack ⭐ NEW
- **Type**: Freemium (API key required)
- **Coverage**: 170,000+ tickers across 70+ exchanges
- **Best for**: Global market coverage, simple integration
- **Rate Limits**: 60 calls/min (varies by plan)
- **Data Quality**: Reliable, easy-to-use API
- **Config**: `MARKETSTACK_API_KEY`
- **Priority**: 6

### 12. CoinGecko ⭐ NEW
- **Type**: Free (no API key for basic features)
- **Coverage**: Cryptocurrency market data
- **Best for**: Free crypto data, market metrics
- **Rate Limits**: 50 calls/min (free tier)
- **Data Quality**: Comprehensive crypto data
- **Config**: None required for basic tier
- **Priority**: 6

### 13. CoinMarketCap ⭐ NEW
- **Type**: Freemium (API key required)
- **Coverage**: Leading cryptocurrency market data
- **Best for**: Crypto market cap, rankings
- **Rate Limits**: 30 calls/day (free tier)
- **Data Quality**: Industry-standard crypto data
- **Config**: `COINMARKETCAP_API_KEY`
- **Priority**: 7

### 14. Quandl (NASDAQ Data Link) ⭐ NEW
- **Type**: Freemium (API key required)
- **Coverage**: Historical data, alternative data, economics
- **Best for**: Quantitative research, historical analysis
- **Rate Limits**: 50 calls/day (free tier)
- **Data Quality**: Curated datasets, academic-grade
- **Config**: `QUANDL_API_KEY`
- **Priority**: 6
- **Note**: Primarily historical data, not real-time

### 15. Mock Provider
- **Type**: Testing/development
- **Coverage**: All asset types (simulated)
- **Best for**: Development, testing, CI/CD
- **Rate Limits**: None
- **Data Quality**: Synthetic data
- **Config**: None required

## Configuration

Add provider API keys to your `.env` file:

```env
# Core Providers
ALPHA_VANTAGE_API_KEY=your_key_here
FMP_API_KEY=your_key_here
NEWSAPI_API_KEY=your_key_here

# New Providers
POLYGON_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
TWELVEDATA_API_KEY=your_key_here
TIINGO_API_KEY=your_key_here
INTRINIO_API_KEY=your_key_here
MARKETSTACK_API_KEY=your_key_here
COINMARKETCAP_API_KEY=your_key_here
QUANDL_API_KEY=your_key_here

# Optional: Crypto exchange API keys
BINANCE_API_KEY=your_key_here
BINANCE_SECRET_KEY=your_secret_here
```

## Provider Selection Strategy

FIML's arbitration engine automatically selects the best provider based on:

1. **Priority**: Higher priority providers are tried first
2. **Availability**: Provider must be initialized and healthy
3. **Asset Support**: Provider must support the requested asset type
4. **Rate Limits**: Provider must not be rate-limited
5. **Data Freshness**: More recent data is preferred

## Getting API Keys

### Free Tier Available
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key
- **FMP**: https://financialmodelingprep.com/developer/docs
- **NewsAPI**: https://newsapi.org/register
- **Polygon.io**: https://polygon.io/
- **Finnhub**: https://finnhub.io/register
- **Twelvedata**: https://twelvedata.com/pricing
- **Tiingo**: https://www.tiingo.com/
- **Marketstack**: https://marketstack.com/product
- **CoinMarketCap**: https://coinmarketcap.com/api/
- **Quandl**: https://data.nasdaq.com/sign-up

### Premium Only
- **Intrinio**: https://intrinio.com/

### No API Key Required
- **Yahoo Finance**: No registration needed
- **CoinGecko**: Free tier available without API key
- **CCXT**: Public data accessible without API key

## Best Practices

1. **Start with free providers**: Yahoo Finance and CoinGecko provide good data without API keys
2. **Add providers incrementally**: Start with 2-3 providers and add more as needed
3. **Monitor rate limits**: Free tiers often have daily/monthly limits
4. **Use priority wisely**: Adjust provider priorities based on your use case
5. **Enable fallback**: The arbitration engine will automatically fall back if a provider fails
6. **Test providers individually**: Use the provider health endpoints to verify configuration

## Provider Priorities

Current default priorities (higher = tried first):
- Priority 8: Polygon.io (premium quality, low latency)
- Priority 7: Alpha Vantage, FMP, Finnhub, Twelvedata, Tiingo, Intrinio, CoinMarketCap
- Priority 6: Marketstack, CoinGecko, Quandl
- Priority 5: Yahoo Finance (reliable free tier)
- Priority 3: CCXT (crypto-specific)
- Priority 1: Mock Provider (testing only)

Priorities can be adjusted in provider initialization code or via configuration.
