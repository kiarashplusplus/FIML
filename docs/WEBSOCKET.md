# WebSocket Streaming Documentation

## Overview

FIML provides real-time WebSocket streaming for financial data, enabling live updates for prices, OHLCV candlesticks, and multi-asset quotes. The WebSocket implementation uses the same arbitration engine and provider stack as the REST API, ensuring consistent data quality and provider selection.

## Features

- **Real-time Price Streaming**: Live price updates with configurable intervals (100ms - 60s)
- **OHLCV Candlestick Streaming**: Real-time candlestick data for technical analysis
- **Multi-Asset Support**: Subscribe to up to 50 symbols simultaneously
- **Automatic Failover**: Uses arbitration engine for provider selection and fallback
- **Connection Management**: Built-in heartbeat, reconnection, and error handling
- **Multiple Stream Types**: Price, OHLCV, quotes, trades, and multi-asset streams

## Endpoints

### 1. Main WebSocket Endpoint: `/ws/stream`

Full-featured endpoint with complete control over subscriptions.

**URL**: `ws://localhost:8000/ws/stream`

### 2. Simplified Price Endpoint: `/ws/prices/{symbols}`

Quick access for price streaming without manual subscription.

**URL**: `ws://localhost:8000/ws/prices/AAPL,GOOGL,MSFT`

### 3. Connection Status Endpoint: `/ws/connections` (HTTP GET)

Get information about active WebSocket connections.

**URL**: `http://localhost:8000/ws/connections`

## Message Types

### Client → Server Messages

#### Subscribe Request

```json
{
  "type": "subscribe",
  "stream_type": "price",
  "symbols": ["AAPL", "GOOGL"],
  "asset_type": "equity",
  "market": "US",
  "interval_ms": 1000,
  "data_type": "price"
}
```

**Fields**:
- `type`: Always "subscribe"
- `stream_type`: "price" | "ohlcv" | "quote" | "trades" | "multi_asset"
- `symbols`: Array of symbols (1-50 items)
- `asset_type`: "equity" | "crypto" | "forex" | "commodity" | "index" | "etf"
- `market`: "US" | "UK" | "EU" | "JP" | "CN" | "HK" | "CRYPTO" | "GLOBAL"
- `interval_ms`: Update interval in milliseconds (100-60000)
- `data_type`: "price" | "ohlcv" | "fundamentals" | etc.

#### Unsubscribe Request

```json
{
  "type": "unsubscribe",
  "stream_type": "price",
  "symbols": ["AAPL"]
}
```

**Fields**:
- `type`: Always "unsubscribe"
- `stream_type`: Stream type to unsubscribe from
- `symbols`: Specific symbols (or null to unsubscribe from all)

### Server → Client Messages

#### Subscription Acknowledgment

```json
{
  "type": "subscription_ack",
  "stream_type": "price",
  "symbols": ["AAPL", "GOOGL"],
  "subscription_id": "uuid-here",
  "interval_ms": 1000,
  "timestamp": "2025-11-22T10:30:00Z"
}
```

#### Data Message (Price Update)

```json
{
  "type": "data",
  "stream_type": "price",
  "subscription_id": "uuid-here",
  "timestamp": "2025-11-22T10:30:01Z",
  "data": [
    {
      "symbol": "AAPL",
      "price": 195.50,
      "change": 2.30,
      "change_percent": 1.19,
      "volume": 45000000,
      "timestamp": "2025-11-22T10:30:01Z",
      "provider": "yahoo_finance",
      "confidence": 0.98
    }
  ]
}
```

#### Data Message (OHLCV Update)

```json
{
  "type": "data",
  "stream_type": "ohlcv",
  "subscription_id": "uuid-here",
  "timestamp": "2025-11-22T10:30:00Z",
  "data": [
    {
      "symbol": "BTC/USDT",
      "timestamp": "2025-11-22T10:30:00Z",
      "open": 45000.00,
      "high": 45500.00,
      "low": 44800.00,
      "close": 45300.00,
      "volume": 1250000.00,
      "is_closed": false
    }
  ]
}
```

#### Heartbeat Message

```json
{
  "type": "heartbeat",
  "timestamp": "2025-11-22T10:30:00Z",
  "active_subscriptions": 2
}
```

#### Error Message

```json
{
  "type": "error",
  "error_code": "SUBSCRIPTION_ERROR",
  "message": "Failed to create subscription: Invalid symbol",
  "timestamp": "2025-11-22T10:30:00Z"
}
```

## Usage Examples

### Python with websockets

```python
import asyncio
import json
import websockets

async def stream_prices():
    uri = "ws://localhost:8000/ws/stream"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to price stream
        subscription = {
            "type": "subscribe",
            "stream_type": "price",
            "symbols": ["AAPL", "TSLA", "NVDA"],
            "asset_type": "equity",
            "market": "US",
            "interval_ms": 2000,
            "data_type": "price"
        }
        
        await websocket.send(json.dumps(subscription))
        
        # Receive acknowledgment
        ack = json.loads(await websocket.recv())
        print(f"Subscribed: {ack}")
        
        # Stream data
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "data":
                for update in data["data"]:
                    print(f"{update['symbol']}: ${update['price']}")

asyncio.run(stream_prices())
```

### JavaScript/TypeScript

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/stream');

ws.onopen = () => {
  // Subscribe to prices
  ws.send(JSON.stringify({
    type: 'subscribe',
    stream_type: 'price',
    symbols: ['AAPL', 'GOOGL'],
    asset_type: 'equity',
    market: 'US',
    interval_ms: 1000,
    data_type: 'price'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'data') {
    data.data.forEach(update => {
      console.log(`${update.symbol}: $${update.price}`);
    });
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### Simplified Price Endpoint

```python
import asyncio
import json
import websockets

async def simple_stream():
    # Auto-subscribes to AAPL and GOOGL
    uri = "ws://localhost:8000/ws/prices/AAPL,GOOGL"
    
    async with websockets.connect(uri) as websocket:
        # Already subscribed, just receive data
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "data":
                for update in data["data"]:
                    print(f"{update['symbol']}: ${update['price']}")

asyncio.run(simple_stream())
```

## Advanced Features

### Multiple Subscriptions

You can create multiple subscriptions on a single WebSocket connection:

```python
async def multi_stream():
    uri = "ws://localhost:8000/ws/stream"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to equity prices
        await websocket.send(json.dumps({
            "type": "subscribe",
            "stream_type": "price",
            "symbols": ["AAPL", "TSLA"],
            "asset_type": "equity",
            "market": "US",
            "interval_ms": 1000,
            "data_type": "price"
        }))
        
        # Subscribe to crypto OHLCV
        await websocket.send(json.dumps({
            "type": "subscribe",
            "stream_type": "ohlcv",
            "symbols": ["BTC/USDT"],
            "asset_type": "crypto",
            "market": "CRYPTO",
            "interval_ms": 5000,
            "data_type": "ohlcv"
        }))
        
        # Process both streams
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "data":
                if data["stream_type"] == "price":
                    # Handle price updates
                    pass
                elif data["stream_type"] == "ohlcv":
                    # Handle OHLCV updates
                    pass
```

### Error Handling and Reconnection

```python
import asyncio
import json
import websockets

async def robust_stream():
    uri = "ws://localhost:8000/ws/prices/AAPL"
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            async with websockets.connect(uri) as websocket:
                print("Connected")
                
                while True:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=60
                        )
                        data = json.loads(message)
                        
                        if data["type"] == "data":
                            # Process data
                            pass
                        elif data["type"] == "error":
                            print(f"Error: {data['message']}")
                            
                    except asyncio.TimeoutError:
                        # Check connection with ping
                        await websocket.ping()
                        
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection closed, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise
```

## Performance Considerations

### Update Intervals

- **100ms-500ms**: High-frequency trading, tick-by-tick data
- **1000ms (1s)**: Real-time monitoring, active trading
- **5000ms (5s)**: Dashboard updates, portfolio monitoring
- **60000ms (60s)**: Long-term tracking, reduced load

### Connection Limits

- Maximum 50 symbols per subscription
- Unlimited subscriptions per connection
- Heartbeat every 30 seconds (configurable)
- Automatic cleanup on disconnect

### Data Freshness

WebSocket streaming uses the same arbitration engine as REST endpoints:
- Provider scoring based on freshness, latency, uptime
- Automatic fallback to backup providers
- Confidence scores included in updates

## Error Codes

| Error Code | Description |
|------------|-------------|
| `INVALID_JSON` | Malformed JSON message |
| `INVALID_MESSAGE_TYPE` | Unknown message type |
| `SUBSCRIPTION_ERROR` | Failed to create subscription |
| `UNSUBSCRIBE_ERROR` | Failed to unsubscribe |
| `PROCESSING_ERROR` | General processing error |

## Testing

Run the WebSocket test suite:

```bash
pytest tests/test_websocket.py -v
```

Run the interactive demo:

```bash
python examples/websocket_streaming.py
```

Quick demo:

```bash
python examples/websocket_demo.py
```

## Integration with Arbitration Engine

The WebSocket streaming system fully integrates with FIML's arbitration engine:

1. **Provider Selection**: Uses arbitration engine to select optimal provider
2. **Automatic Fallback**: Falls back to backup providers on failure
3. **Data Quality**: Same confidence scoring as REST endpoints
4. **Provider Diversity**: Can stream from Yahoo Finance, Alpha Vantage, FMP, CCXT

## Security Considerations

- No authentication required for public data (configurable)
- Rate limiting per connection (configurable)
- Automatic connection cleanup
- Input validation on all messages
- No financial advice disclaimer included

## Monitoring

Check active connections:

```bash
curl http://localhost:8000/ws/connections
```

Response:
```json
{
  "active_connections": 5,
  "total_subscriptions": 12,
  "subscribed_symbols": ["AAPL", "GOOGL", "TSLA", "BTC/USDT"]
}
```

## Future Enhancements

- [ ] Trade streaming
- [ ] Order book depth streaming
- [ ] News feed streaming
- [ ] Alert/notification system
- [ ] Snapshot support
- [ ] Replay functionality
