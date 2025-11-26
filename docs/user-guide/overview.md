# User Guide Overview

Welcome to the FIML User Guide! This section provides comprehensive documentation on using FIML for financial data access and analysis.

## What is FIML?

FIML (Financial Intelligence Meta-Layer) is an AI-native financial data platform that provides intelligent access to multiple data providers through a unified API.

## Key Concepts

### MCP Protocol

FIML implements the Model Context Protocol (MCP) for standardized tool interaction. Learn more in [MCP Tools](mcp-tools.md).

### Data Arbitration

The arbitration engine automatically selects the best data provider based on multiple factors. See [Architecture](../architecture/arbitration.md) for details.

### Caching Strategy

Multi-tier caching ensures fast data access while minimizing API costs. Learn about our [Caching Strategy](../architecture/caching.md).

## Common Use Cases

- **Real-time Market Data**: Stream prices and OHLCV data via WebSocket
- **Technical Analysis**: Calculate indicators and patterns
- **Portfolio Monitoring**: Track multiple assets simultaneously
- **Market Research**: Query fundamentals and historical data

## Getting Help

- Check the [API Reference](../api/rest.md)
- Browse [Examples](https://github.com/kiarashplusplus/FIML/tree/main/examples)
- Join our [Discord](https://discord.gg/fiml)

## FAQ

### General Questions

**Q: What data providers does FIML support?**  
A: FIML supports Yahoo Finance, Alpha Vantage, Financial Modeling Prep (FMP), and CCXT for cryptocurrency data. See the [Providers](../PROVIDERS.md) documentation.

**Q: How do I get started?**  
A: Check the [Installation Guide](../getting-started/installation.md) and [Quick Start](../getting-started/quickstart.md).

**Q: Does FIML support real-time data?**  
A: Yes! FIML supports WebSocket streaming for real-time price updates. See [WebSocket Streaming](websocket.md).

**Q: How is data cached?**  
A: FIML uses a two-tier caching system with Redis (L1) and PostgreSQL (L2). See [Caching Strategy](../architecture/caching.md).

**Q: Can I use FIML with ChatGPT or Claude?**  
A: Yes! FIML implements the Model Context Protocol (MCP) which is supported by both platforms. See [MCP Tools](mcp-tools.md).
