# Architecture Overview

FIML is built with a modular, scalable architecture designed for high performance and extensibility.

## System Layers

### Client Layer

Supports multiple client types:
- ChatGPT plugins
- Claude Desktop integration
- Custom applications
- Telegram bots

### API Gateway

Unified MCP API with:
- Request routing
- Authentication
- Rate limiting
- Compliance checks

### Data Arbitration Engine

Intelligent provider selection based on:
- Availability (30%)
- Freshness (25%)
- Reliability (25%)
- Latency (15%)
- Cost (5%)

### Multi-Agent Framework

Ray-based distributed agents:
- Fundamentals analysis
- Technical analysis
- Macro analysis
- Sentiment analysis
- News aggregation

### Provider Layer

Multiple data sources:
- Yahoo Finance
- Alpha Vantage
- Financial Modeling Prep (FMP)
- CCXT (crypto exchanges)
- Custom providers

## Key Design Principles

1. **Provider Agnostic**: Easy to add new data sources
2. **Cache-First**: Multi-tier caching for performance
3. **Fault Tolerant**: Automatic fallback and retry
4. **Observable**: Comprehensive monitoring and logging
5. **Compliant**: Built-in regional compliance

See detailed architecture docs:
- [Data Arbitration](arbitration.md)
- [Caching Strategy](caching.md)
- [Provider System](providers.md)
