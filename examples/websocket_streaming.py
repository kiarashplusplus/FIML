"""
WebSocket Streaming Example

Demonstrates real-time financial data streaming using WebSocket connections.

This example shows:
1. Connecting to the WebSocket endpoint
2. Subscribing to price streams
3. Receiving real-time updates
4. Managing multiple subscriptions
5. Handling errors and reconnection
"""

import asyncio
import json
from datetime import datetime

import websockets


async def stream_prices_simple():
    """
    Simple example: Stream prices for multiple symbols

    Uses the simplified /ws/prices/{symbols} endpoint
    """
    print("=== Simple Price Streaming ===\n")

    uri = "ws://localhost:8000/ws/prices/AAPL,GOOGL,MSFT"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")

            # Receive subscription acknowledgment
            ack = await websocket.recv()
            ack_data = json.loads(ack)
            print(f"Subscribed: {ack_data}")
            print()

            # Receive price updates
            print("Receiving price updates (Ctrl+C to stop):\n")
            while True:
                message = await websocket.recv()
                data = json.loads(message)

                if data.get("type") == "data":
                    # Print price updates
                    for update in data["data"]:
                        print(
                            f"[{update['timestamp']}] {update['symbol']}: "
                            f"${update['price']:.2f} ({update['change_percent']:+.2f}%) "
                            f"[{update['provider']}]"
                        )
                elif data.get("type") == "heartbeat":
                    print(f"❤️  Heartbeat - {data['active_subscriptions']} active subscriptions")

    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")
    except KeyboardInterrupt:
        print("\nStopped by user")


async def stream_with_full_control():
    """
    Advanced example: Full control over subscriptions

    Uses the main /ws/stream endpoint with subscription messages
    """
    print("\n=== Advanced Streaming with Full Control ===\n")

    uri = "ws://localhost:8000/ws/stream"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")

            # Subscribe to price stream for equities
            equity_subscription = {
                "type": "subscribe",
                "stream_type": "price",
                "symbols": ["AAPL", "TSLA", "NVDA"],
                "asset_type": "equity",
                "market": "US",
                "interval_ms": 2000,  # Update every 2 seconds
                "data_type": "price"
            }

            await websocket.send(json.dumps(equity_subscription))
            ack1 = json.loads(await websocket.recv())
            print(f"Equity subscription created: {ack1['subscription_id']}")

            # Subscribe to OHLCV stream for crypto
            crypto_subscription = {
                "type": "subscribe",
                "stream_type": "ohlcv",
                "symbols": ["BTC/USDT"],
                "asset_type": "crypto",
                "market": "CRYPTO",
                "interval_ms": 5000,  # Update every 5 seconds
                "data_type": "ohlcv"
            }

            await websocket.send(json.dumps(crypto_subscription))
            ack2 = json.loads(await websocket.recv())
            print(f"Crypto subscription created: {ack2['subscription_id']}")
            print()

            # Receive updates
            print("Receiving updates from multiple streams:\n")

            update_count = 0
            while update_count < 20:  # Receive 20 updates then stop
                message = await websocket.recv()
                data = json.loads(message)

                if data.get("type") == "data":
                    stream_type = data["stream_type"]

                    if stream_type == "price":
                        for update in data["data"]:
                            print(
                                f"💵 PRICE: {update['symbol']} = ${update['price']:.2f} "
                                f"({update['change_percent']:+.2f}%)"
                            )
                    elif stream_type == "ohlcv":
                        for update in data["data"]:
                            print(
                                f"📊 OHLCV: {update['symbol']} - "
                                f"O:{update['open']:.2f} H:{update['high']:.2f} "
                                f"L:{update['low']:.2f} C:{update['close']:.2f} "
                                f"V:{update['volume']:.0f}"
                            )

                    update_count += 1

                elif data.get("type") == "heartbeat":
                    print("❤️  Heartbeat")

                elif data.get("type") == "error":
                    print(f"❌ Error: {data['message']}")

            # Unsubscribe from equity stream
            print("\nUnsubscribing from equity stream...")
            unsubscribe = {
                "type": "unsubscribe",
                "stream_type": "price",
                "symbols": None  # Unsubscribe from all price streams
            }
            await websocket.send(json.dumps(unsubscribe))

            unsub_ack = json.loads(await websocket.recv())
            print(f"Unsubscribed: {unsub_ack}")

    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")
    except KeyboardInterrupt:
        print("\nStopped by user")


async def stream_with_error_handling():
    """
    Robust example: Automatic reconnection and error handling
    """
    print("\n=== Streaming with Auto-Reconnection ===\n")

    uri = "ws://localhost:8000/ws/prices/AAPL,GOOGL"
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"Connection attempt {attempt + 1}/{max_retries}")

            async with websockets.connect(uri) as websocket:
                print("✅ Connected successfully")

                # Receive subscription ACK
                ack = json.loads(await websocket.recv())
                print(f"Subscribed to: {', '.join(ack['symbols'])}\n")

                # Stream data
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=60)
                        data = json.loads(message)

                        if data.get("type") == "data":
                            timestamp = datetime.fromisoformat(
                                data["timestamp"].replace("Z", "+00:00")
                            )
                            for update in data["data"]:
                                print(
                                    f"[{timestamp.strftime('%H:%M:%S')}] "
                                    f"{update['symbol']}: ${update['price']:.2f}"
                                )

                    except asyncio.TimeoutError:
                        print("⚠️  No data received in 60s, checking connection...")
                        # Send a ping to check if connection is alive
                        await websocket.ping()

        except websockets.exceptions.ConnectionClosed as e:
            print(f"❌ Connection closed: {e}")
            if attempt < max_retries - 1:
                print(f"Reconnecting in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                print("Max retries reached, giving up")
                break

        except KeyboardInterrupt:
            print("\n👋 Stopped by user")
            break


async def monitor_multiple_assets():
    """
    Practical example: Monitor a portfolio of assets
    """
    print("\n=== Portfolio Monitoring ===\n")

    # Portfolio to monitor
    portfolio = {
        "Tech Stocks": ["AAPL", "GOOGL", "MSFT", "NVDA"],
        "Crypto": ["BTC/USDT", "ETH/USDT"],
    }

    uri = "ws://localhost:8000/ws/stream"

    try:
        async with websockets.connect(uri) as websocket:
            print("📊 Starting portfolio monitor...\n")

            # Subscribe to tech stocks
            tech_sub = {
                "type": "subscribe",
                "stream_type": "price",
                "symbols": portfolio["Tech Stocks"],
                "asset_type": "equity",
                "market": "US",
                "interval_ms": 3000,
                "data_type": "price"
            }
            await websocket.send(json.dumps(tech_sub))
            json.loads(await websocket.recv())
            print(f"✅ Monitoring tech stocks: {portfolio['Tech Stocks']}")

            # Subscribe to crypto
            crypto_sub = {
                "type": "subscribe",
                "stream_type": "price",
                "symbols": portfolio["Crypto"],
                "asset_type": "crypto",
                "market": "CRYPTO",
                "interval_ms": 3000,
                "data_type": "price"
            }
            await websocket.send(json.dumps(crypto_sub))
            json.loads(await websocket.recv())
            print(f"✅ Monitoring crypto: {portfolio['Crypto']}\n")

            # Track portfolio value
            prices = {}

            while True:
                message = await websocket.recv()
                data = json.loads(message)

                if data.get("type") == "data":
                    for update in data["data"]:
                        symbol = update["symbol"]
                        price = update["price"]
                        change_pct = update["change_percent"]

                        prices[symbol] = price

                        # Color code by change
                        color = "🟢" if change_pct >= 0 else "🔴"

                        print(
                            f"{color} {symbol:12} ${price:>10.2f} "
                            f"({change_pct:>+6.2f}%) "
                            f"[{update['provider']}]"
                        )

                    print(f"\nTracking {len(prices)} assets\n")

    except KeyboardInterrupt:
        print("\n👋 Portfolio monitor stopped")


async def main():
    """
    Run examples
    """
    print("=" * 60)
    print("FIML WebSocket Streaming Examples")
    print("=" * 60)
    print("\nMake sure the FIML server is running:")
    print("  uvicorn fiml.server:app --reload")
    print("\n" + "=" * 60 + "\n")

    # Choose which example to run
    examples = {
        "1": ("Simple Price Streaming", stream_prices_simple),
        "2": ("Advanced Multi-Stream", stream_with_full_control),
        "3": ("Auto-Reconnection", stream_with_error_handling),
        "4": ("Portfolio Monitor", monitor_multiple_assets),
    }

    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")

    choice = input("\nSelect example (1-4, or 'all'): ").strip()

    if choice == "all":
        # Run all examples sequentially
        for name, func in examples.values():
            print(f"\n{'=' * 60}")
            print(f"Running: {name}")
            print(f"{'=' * 60}\n")
            await func()
            await asyncio.sleep(2)
    elif choice in examples:
        name, func = examples[choice]
        await func()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
