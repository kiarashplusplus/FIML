# Quick Start

Get up and running with FIML in minutes! This guide will walk you through making your first API call and executing your first FK-DSL query.

## Prerequisites

Make sure you have completed the [Installation](installation.md) guide and all services are running.

## Verify Installation

First, check that FIML is running:

```bash
curl http://localhost:8000/health
```

## Using MCP Tools

FIML provides several MCP (Model Context Protocol) tools for financial data access.

### 1. Search by Symbol (Equity)

Query stock data using a symbol:

```json
{
  "name": "search-by-symbol",
  "arguments": {
    "symbol": "TSLA",
    "market": "US",
    "depth": "standard",
    "language": "en"
  }
}
```

Example using `curl`:

```bash
curl -X POST http://localhost:8000/mcp/tools/search-by-symbol \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TSLA",
    "market": "US",
    "depth": "standard"
  }'
```

### 2. Search by Coin (Cryptocurrency)

Query cryptocurrency data:

```json
{
  "name": "search-by-coin",
  "arguments": {
    "symbol": "BTC",
    "exchange": "binance",
    "pair": "USDT",
    "depth": "deep"
  }
}
```

Example using `curl`:

```bash
curl -X POST http://localhost:8000/mcp/tools/search-by-coin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "exchange": "binance",
    "pair": "USDT"
  }'
```

### 3. Execute FK-DSL Query

Execute complex queries using our Financial Knowledge DSL:

```bash
curl -X POST http://localhost:8000/mcp/tools/execute-fk-dsl \
  -H "Content-Type: application/json" \
  -d '{
    "query": "EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY)"
  }'
```

## WebSocket Streaming

For real-time data, use our WebSocket endpoints.

### Simple Price Streaming

Create a Python script (`stream_prices.py`):

```python
import asyncio
import websockets
import json

async def stream_prices():
    uri = "ws://localhost:8000/ws/prices/AAPL,GOOGL,MSFT"
    
    async with websockets.connect(uri) as websocket:
        print("Connected and streaming...")
        
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "data":
                for update in data["data"]:
                    print(f"{update['symbol']}: ${update['price']:.2f} "
                          f"({update['change_percent']:+.2f}%)")

asyncio.run(stream_prices())
```

Run it:

```bash
python stream_prices.py
```

### Advanced WebSocket Control

For more control over subscriptions:

```python
async def advanced_streaming():
    uri = "ws://localhost:8000/ws/stream"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to price stream
        subscription = {
            "type": "subscribe",
            "stream_type": "price",
            "symbols": ["AAPL", "TSLA"],
            "asset_type": "equity",
            "market": "US",
            "interval_ms": 1000,
            "data_type": "price"
        }
        
        await websocket.send(json.dumps(subscription))
        
        # Receive subscription acknowledgment
        ack = await websocket.recv()
        print(f"Subscribed: {ack}")
        
        # Stream data
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "data":
                for update in data["data"]:
                    print(f"Price update: {update}")
```

## FK-DSL Query Examples

The Financial Knowledge DSL (FK-DSL) provides a powerful query language for complex financial analysis.

### Comprehensive Equity Analysis

```fkdsl
EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY), TECHNICAL(RSI, MACD)
```

This query will:
- Get current price for TSLA
- Calculate 30-day volatility
- Compute correlation with BTC and SPY
- Calculate RSI and MACD indicators

### Compare Cryptocurrencies

```fkdsl
COMPARE BTC vs ETH vs SOL ON: VOLUME(7d), LIQUIDITY, MOMENTUM(14d), NETWORK_HEALTH
```

### Macro Analysis

```fkdsl
MACRO: US10Y, CPI, VIX, DXY → REGRESSION ON SPY
```

### Market Scan

```fkdsl
SCAN NASDAQ WHERE VOLUME > AVG_VOLUME(30d) * 2 AND PRICE_CHANGE(1d) > 5%
```

## Interactive API Documentation

Explore all available endpoints using the interactive Swagger UI:

1. Open your browser and navigate to: [http://localhost:8000/docs](http://localhost:8000/docs)
2. Browse available endpoints
3. Try out API calls directly in the browser
4. View request/response schemas

## Live Demo Script

FIML includes a comprehensive demo script that exercises all major features:

```bash
bash live_demo.sh
```

This will test:
- System health checks
- MCP tool discovery
- Real-time stock data (AAPL, TSLA)
- Cryptocurrency queries (BTC)
- Service status

## Monitoring

Access monitoring dashboards:

- **Prometheus Metrics**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **WebSocket Connections**: [http://localhost:8000/ws/connections](http://localhost:8000/ws/connections)
- **Grafana Dashboards**: [http://localhost:3000](http://localhost:3000) (admin/admin)
- **Ray Dashboard**: [http://localhost:8265](http://localhost:8265)

## Common Use Cases

### Portfolio Monitoring

Monitor multiple assets in real-time:

```python
symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
uri = f"ws://localhost:8000/ws/prices/{','.join(symbols)}"

async with websockets.connect(uri) as ws:
    while True:
        data = json.loads(await ws.recv())
        # Process portfolio updates
```

### Technical Analysis

Analyze technical indicators:

```bash
curl -X POST http://localhost:8000/mcp/tools/execute-fk-dsl \
  -H "Content-Type: application/json" \
  -d '{
    "query": "EVALUATE AAPL: TECHNICAL(RSI, MACD, BOLLINGER_BANDS, SMA(50), SMA(200))"
  }'
```

### Multi-Asset Correlation

Analyze correlations between different asset classes:

```bash
curl -X POST http://localhost:8000/mcp/tools/execute-fk-dsl \
  -H "Content-Type: application/json" \
  -d '{
    "query": "CORRELATE SPY, QQQ, BTC, GLD, TLT PERIOD(90d)"
  }'
```

## Next Steps

Now that you're up and running:

- Learn about [Configuration Options](configuration.md)
- Explore [MCP Tools](../user-guide/mcp-tools.md) in detail
- Understand [WebSocket Streaming](../user-guide/websocket.md)
- Master [FK-DSL Query Language](../user-guide/fk-dsl.md)
- Review [Architecture](../architecture/overview.md)

## Getting Help

- Check the [API Reference](../api/rest.md)
- Join our [Discord community](https://discord.gg/fiml)
- Report issues on [GitHub](https://github.com/kiarashplusplus/FIML/issues)
