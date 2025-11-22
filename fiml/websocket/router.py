"""
WebSocket Router

Provides WebSocket endpoints for real-time financial data streaming.
"""

import json
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from fiml.core.logging import get_logger
from fiml.websocket.manager import websocket_manager
from fiml.websocket.models import (
    MessageType,
    SubscriptionRequest,
    UnsubscribeRequest,
)

logger = get_logger(__name__)

websocket_router = APIRouter()


@websocket_router.websocket("/stream")
async def websocket_stream_endpoint(websocket: WebSocket) -> None:
    """
    Main WebSocket streaming endpoint

    Supports:
    - Real-time price updates
    - OHLCV candlestick streaming
    - Multi-asset quotes
    - Subscription management

    Message Format:
    {
        "type": "subscribe",
        "stream_type": "price",
        "symbols": ["AAPL", "GOOGL"],
        "asset_type": "equity",
        "market": "US",
        "interval_ms": 1000,
        "data_type": "price"
    }
    """
    connection_id = await websocket_manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                logger.debug(
                    "Received WebSocket message",
                    connection_id=connection_id,
                    type=message_type,
                )

                if message_type == MessageType.SUBSCRIBE:
                    # Handle subscription request
                    try:
                        request = SubscriptionRequest(**message)
                        response = await websocket_manager.subscribe(
                            websocket, connection_id, request
                        )
                        await websocket.send_json(response.model_dump(mode="json"))

                        logger.info(
                            "Subscription created",
                            connection_id=connection_id,
                            subscription_id=response.subscription_id,
                            symbols=response.symbols,
                        )

                    except Exception as e:
                        logger.error(f"Subscription error: {e}")
                        await websocket_manager.send_error(
                            websocket,
                            "SUBSCRIPTION_ERROR",
                            f"Failed to create subscription: {str(e)}",
                        )

                elif message_type == MessageType.UNSUBSCRIBE:
                    # Handle unsubscribe request
                    try:
                        request = UnsubscribeRequest(**message)
                        await websocket_manager.unsubscribe(websocket, connection_id, request)

                        # Send acknowledgment
                        await websocket.send_json(
                            {
                                "type": "unsubscribe_ack",
                                "stream_type": request.stream_type,
                                "symbols": request.symbols,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Unsubscribe error: {e}")
                        await websocket_manager.send_error(
                            websocket, "UNSUBSCRIBE_ERROR", f"Failed to unsubscribe: {str(e)}"
                        )

                else:
                    await websocket_manager.send_error(
                        websocket, "INVALID_MESSAGE_TYPE", f"Unknown message type: {message_type}"
                    )

            except json.JSONDecodeError:
                await websocket_manager.send_error(
                    websocket, "INVALID_JSON", "Message is not valid JSON"
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket_manager.send_error(
                    websocket, "PROCESSING_ERROR", f"Error processing message: {str(e)}"
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected", connection_id=connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", connection_id=connection_id)
    finally:
        await websocket_manager.disconnect(websocket, connection_id)


@websocket_router.websocket("/prices/{symbols}")
async def websocket_prices_endpoint(websocket: WebSocket, symbols: str) -> None:
    """
    Simplified price streaming endpoint

    Usage: ws://localhost:8000/ws/prices/AAPL,GOOGL,MSFT

    Automatically subscribes to price updates for the specified symbols.
    """
    connection_id = await websocket_manager.connect(websocket)

    try:
        # Parse symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",")]

        # Auto-subscribe to price stream
        request = SubscriptionRequest(
            stream_type="price",
            symbols=symbol_list,
            asset_type="equity",
            market="US",
            interval_ms=1000,
            data_type="price",
        )

        response = await websocket_manager.subscribe(websocket, connection_id, request)
        await websocket.send_json(response.model_dump(mode="json"))

        logger.info(
            "Auto-subscribed to prices",
            connection_id=connection_id,
            symbols=symbol_list,
        )

        # Keep connection alive and listen for close
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Error in prices endpoint: {e}", connection_id=connection_id)
    finally:
        await websocket_manager.disconnect(websocket, connection_id)


@websocket_router.get("/connections")
async def get_active_connections() -> Dict:
    """Get information about active WebSocket connections"""
    active_count = len(websocket_manager.active_connections)
    total_subscriptions = sum(
        len(subs) for subs in websocket_manager.subscriptions.values()
    )

    return {
        "active_connections": active_count,
        "total_subscriptions": total_subscriptions,
        "subscribed_symbols": list(websocket_manager.symbol_subscriptions.keys()),
    }
