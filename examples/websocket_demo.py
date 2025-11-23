#!/usr/bin/env python3
"""
Quick WebSocket Demo

Demonstrates the WebSocket streaming functionality with the FIML server.
"""

import asyncio
import json

import websockets


async def quick_demo():
    """Quick demonstration of WebSocket streaming"""
    print("=" * 60)
    print("FIML WebSocket Streaming Demo")
    print("=" * 60)
    print()

    # Note: This assumes the server is running on localhost:8000
    # Start the server with: uvicorn fiml.server:app --reload

    uri = "ws://localhost:8000/ws/prices/AAPL,GOOGL"

    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            print()

            # Receive subscription acknowledgment
            ack = await websocket.recv()
            ack_data = json.loads(ack)
            print("📨 Subscription Acknowledged:")
            print(f"   Subscription ID: {ack_data['subscription_id']}")
            print(f"   Symbols: {', '.join(ack_data['symbols'])}")
            print(f"   Update Interval: {ack_data['interval_ms']}ms")
            print()

            print("📊 Streaming data (receiving 5 updates)...")
            print("-" * 60)

            # Receive 5 data updates
            count = 0
            while count < 5:
                message = await websocket.recv()
                data = json.loads(message)

                if data.get("type") == "data":
                    count += 1
                    print(f"\n📈 Update #{count}:")
                    for update in data["data"]:
                        print(f"   {update['symbol']:6} | "
                              f"Price: ${update['price']:>8.2f} | "
                              f"Change: {update['change_percent']:>+6.2f}% | "
                              f"Provider: {update['provider']}")
                elif data.get("type") == "heartbeat":
                    print("   ❤️  Heartbeat received")
                elif data.get("type") == "error":
                    print(f"   ❌ Error: {data['message']}")
                    break

            print()
            print("-" * 60)
            print("✅ Demo completed successfully!")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed: {e}")
    except ConnectionRefusedError:
        print("❌ Connection refused. Make sure the FIML server is running:")
        print("   uvicorn fiml.server:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(quick_demo())
