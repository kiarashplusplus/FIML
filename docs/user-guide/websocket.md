# WebSocket Streaming

FIML provides WebSocket endpoints for real-time financial data streaming.

## Endpoints

### Simple Price Streaming

```
ws://localhost:8000/ws/prices/{symbols}
```

Auto-subscribes to price updates for the specified symbols.

### Advanced Streaming

```
ws://localhost:8000/ws/stream
```

Supports manual subscription management for multiple streams.

## Examples

See the [Quick Start Guide](../getting-started/quickstart.md#websocket-streaming) for detailed examples.

## Features

- Real-time price updates
- OHLCV candlestick data
- Multi-symbol subscriptions (up to 50)
- Auto-reconnection with heartbeat
- Configurable update intervals
