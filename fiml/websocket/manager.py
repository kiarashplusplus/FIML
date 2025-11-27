"""
WebSocket Connection Manager

Handles WebSocket connections, subscriptions, and real-time data streaming
using the provider and arbitration stack.
"""

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Set

from fastapi import WebSocket

from fiml.arbitration.engine import arbitration_engine
from fiml.core.exceptions import NoProviderAvailableError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.websocket.models import (
    HeartbeatMessage,
    OHLCVUpdate,
    PriceUpdate,
    StreamMessage,
    StreamType,
    SubscriptionRequest,
    SubscriptionResponse,
    UnsubscribeRequest,
    WebSocketError,
)

logger = get_logger(__name__)


class Subscription:
    """Represents an active subscription"""

    def __init__(
        self,
        subscription_id: str,
        websocket: WebSocket,
        stream_type: StreamType,
        symbols: List[str],
        asset_type: AssetType,
        market: Market,
        interval_ms: int,
        data_type: DataType,
        params: Dict,
    ):
        self.subscription_id = subscription_id
        self.websocket = websocket
        self.stream_type = stream_type
        self.symbols = symbols
        self.asset_type = asset_type
        self.market = market
        self.interval_ms = interval_ms
        self.data_type = data_type
        self.params = params
        self.created_at = datetime.now(timezone.utc)
        self.last_update = datetime.now(timezone.utc)
        self._task: asyncio.Task | None = None

    def start_streaming(self, callback: Callable) -> None:
        """Start the streaming task"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(callback(self))

    def stop_streaming(self) -> None:
        """Stop the streaming task"""
        if self._task and not self._task.done():
            self._task.cancel()


class WebSocketManager:
    """
    Manages WebSocket connections and subscriptions

    Features:
    - Connection lifecycle management
    - Multi-symbol subscriptions
    - Real-time data streaming from arbitration engine
    - Automatic heartbeats
    - Error handling and reconnection
    """

    def __init__(self) -> None:
        # Active connections
        self.active_connections: Set[WebSocket] = set()

        # Subscriptions: connection_id -> {subscription_id -> Subscription}
        self.subscriptions: Dict[str, Dict[str, Subscription]] = defaultdict(dict)

        # Symbol subscriptions: symbol -> {subscription_ids}
        self.symbol_subscriptions: Dict[str, Set[str]] = defaultdict(set)

        # Heartbeat interval (seconds)
        self.heartbeat_interval = 30

        # Streaming tasks
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections.add(websocket)

        logger.info("WebSocket connected", connection_id=connection_id)

        # Start heartbeat for this connection
        self._heartbeat_tasks[connection_id] = asyncio.create_task(
            self._send_heartbeats(websocket, connection_id)
        )

        return connection_id

    async def disconnect(self, websocket: WebSocket, connection_id: str) -> None:
        """Handle WebSocket disconnection"""
        # Cancel all subscriptions for this connection
        if connection_id in self.subscriptions:
            for sub_id, subscription in self.subscriptions[connection_id].items():
                subscription.stop_streaming()
                # Remove from symbol subscriptions
                for symbol in subscription.symbols:
                    self.symbol_subscriptions[symbol].discard(sub_id)

            del self.subscriptions[connection_id]

        # Cancel heartbeat task
        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
            del self._heartbeat_tasks[connection_id]

        # Remove connection
        self.active_connections.discard(websocket)

        logger.info("WebSocket disconnected", connection_id=connection_id)

    async def subscribe(
        self, websocket: WebSocket, connection_id: str, request: SubscriptionRequest
    ) -> SubscriptionResponse:
        """
        Handle subscription request

        Creates a new subscription and starts streaming data
        """
        subscription_id = str(uuid.uuid4())

        logger.info(
            "Creating subscription",
            connection_id=connection_id,
            subscription_id=subscription_id,
            stream_type=request.stream_type,
            symbols=request.symbols,
        )

        # Create subscription
        subscription = Subscription(
            subscription_id=subscription_id,
            websocket=websocket,
            stream_type=request.stream_type,
            symbols=request.symbols,
            asset_type=request.asset_type,
            market=request.market,
            interval_ms=request.interval_ms,
            data_type=request.data_type,
            params=request.params,
        )

        # Store subscription
        self.subscriptions[connection_id][subscription_id] = subscription

        # Track symbol subscriptions
        for symbol in request.symbols:
            self.symbol_subscriptions[symbol].add(subscription_id)

        # Start streaming task based on stream type
        if request.stream_type == StreamType.PRICE:
            subscription.start_streaming(self._stream_prices)
        elif request.stream_type == StreamType.OHLCV:
            subscription.start_streaming(self._stream_ohlcv)
        elif request.stream_type == StreamType.MULTI_ASSET:
            subscription.start_streaming(self._stream_multi_asset)
        else:
            # For other stream types, use price as default
            subscription.start_streaming(self._stream_prices)

        return SubscriptionResponse(
            stream_type=request.stream_type,
            symbols=request.symbols,
            subscription_id=subscription_id,
            interval_ms=request.interval_ms,
        )

    async def unsubscribe(
        self, websocket: WebSocket, connection_id: str, request: UnsubscribeRequest
    ) -> None:
        """Handle unsubscribe request"""
        if connection_id not in self.subscriptions:
            return

        # If no symbols specified, unsubscribe from all with matching stream type
        if request.symbols is None:
            for sub_id, sub in list(self.subscriptions[connection_id].items()):
                if sub.stream_type == request.stream_type:
                    sub.stop_streaming()
                    # Remove from symbol tracking
                    for symbol in sub.symbols:
                        self.symbol_subscriptions[symbol].discard(sub_id)
                    del self.subscriptions[connection_id][sub_id]
        else:
            # Unsubscribe from specific symbols
            for sub_id, sub in list(self.subscriptions[connection_id].items()):
                if sub.stream_type == request.stream_type:
                    # Remove matching symbols
                    remaining_symbols = [s for s in sub.symbols if s not in request.symbols]
                    if not remaining_symbols:
                        # No symbols left, remove subscription
                        sub.stop_streaming()
                        for symbol in sub.symbols:
                            self.symbol_subscriptions[symbol].discard(sub_id)
                        del self.subscriptions[connection_id][sub_id]
                    else:
                        # Update subscription with remaining symbols
                        sub.symbols = remaining_symbols

        logger.info(
            "Unsubscribed",
            connection_id=connection_id,
            stream_type=request.stream_type,
            symbols=request.symbols,
        )

    async def send_error(self, websocket: WebSocket, error_code: str, message: str) -> None:
        """Send error message to client"""
        error = WebSocketError(error_code=error_code, message=message)
        try:
            await websocket.send_json(error.model_dump(mode="json"))
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    async def _send_heartbeats(self, websocket: WebSocket, connection_id: str) -> None:
        """Send periodic heartbeat messages"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                # Count active subscriptions
                active_subs = len(self.subscriptions.get(connection_id, {}))

                heartbeat = HeartbeatMessage(active_subscriptions=active_subs)
                await websocket.send_json(heartbeat.model_dump(mode="json"))

                logger.debug(
                    "Sent heartbeat",
                    connection_id=connection_id,
                    active_subscriptions=active_subs,
                )
        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled", connection_id=connection_id)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}", connection_id=connection_id)

    async def _stream_prices(self, subscription: Subscription) -> None:
        """
        Stream real-time price updates

        Uses the arbitration engine to fetch data from optimal providers
        """
        try:
            interval_sec = subscription.interval_ms / 1000.0

            while True:
                try:
                    updates = []

                    for symbol in subscription.symbols:
                        # Create asset
                        asset = Asset(
                            symbol=symbol,
                            asset_type=subscription.asset_type,
                            market=subscription.market,
                        )

                        try:
                            # Get arbitration plan
                            plan = await arbitration_engine.arbitrate_request(
                                asset=asset,
                                data_type=DataType.PRICE,
                                user_region="US",
                            )

                            # Execute with fallback
                            response = await arbitration_engine.execute_with_fallback(
                                plan=plan, asset=asset, data_type=DataType.PRICE
                            )

                            # Extract price data
                            price_data = response.data
                            current_price = price_data.get("price", 0.0)

                            # Create price update
                            update = PriceUpdate(
                                symbol=symbol,
                                price=current_price,
                                change=price_data.get("change", 0.0),
                                change_percent=price_data.get("change_percent", 0.0),
                                volume=price_data.get("volume"),
                                timestamp=response.timestamp,
                                provider=response.provider,
                                confidence=response.confidence,
                            )
                            updates.append(update)

                        except NoProviderAvailableError:
                            logger.warning(f"No provider available for {symbol}")
                        except Exception as e:
                            logger.error(f"Error fetching price for {symbol}: {e}")

                    # Send updates if any
                    if updates:
                        message = StreamMessage(
                            stream_type=StreamType.PRICE,
                            subscription_id=subscription.subscription_id,
                            data=[u.model_dump(mode="json") for u in updates],
                        )

                        await subscription.websocket.send_json(message.model_dump(mode="json"))
                        subscription.last_update = datetime.now(timezone.utc)

                    # Wait for next interval
                    await asyncio.sleep(interval_sec)

                except Exception as e:
                    logger.error(f"Error in price streaming loop: {e}")
                    await asyncio.sleep(interval_sec)

        except asyncio.CancelledError:
            logger.debug("Price streaming cancelled", subscription_id=subscription.subscription_id)
        except Exception as e:
            logger.error(f"Fatal error in price streaming: {e}")

    async def _stream_ohlcv(self, subscription: Subscription) -> None:
        """
        Stream real-time OHLCV (candlestick) updates

        Uses the arbitration engine to fetch OHLCV data
        """
        try:
            interval_sec = subscription.interval_ms / 1000.0

            while True:
                try:
                    updates = []

                    for symbol in subscription.symbols:
                        asset = Asset(
                            symbol=symbol,
                            asset_type=subscription.asset_type,
                            market=subscription.market,
                        )

                        try:
                            # Get arbitration plan
                            plan = await arbitration_engine.arbitrate_request(
                                asset=asset,
                                data_type=DataType.OHLCV,
                                user_region="US",
                            )

                            # Execute with fallback
                            response = await arbitration_engine.execute_with_fallback(
                                plan=plan, asset=asset, data_type=DataType.OHLCV
                            )

                            # Extract latest candle
                            candles = response.data.get("candles", [])
                            if candles:
                                latest = candles[-1]
                                update = OHLCVUpdate(
                                    symbol=symbol,
                                    timestamp=latest.get("timestamp", response.timestamp),
                                    open=latest.get("open", 0.0),
                                    high=latest.get("high", 0.0),
                                    low=latest.get("low", 0.0),
                                    close=latest.get("close", 0.0),
                                    volume=latest.get("volume", 0.0),
                                    is_closed=latest.get("is_closed", False),
                                )
                                updates.append(update)

                        except NoProviderAvailableError:
                            logger.warning(f"No provider available for {symbol}")
                        except Exception as e:
                            logger.error(f"Error fetching OHLCV for {symbol}: {e}")

                    # Send updates
                    if updates:
                        message = StreamMessage(
                            stream_type=StreamType.OHLCV,
                            subscription_id=subscription.subscription_id,
                            data=[u.model_dump(mode="json") for u in updates],
                        )

                        await subscription.websocket.send_json(message.model_dump(mode="json"))
                        subscription.last_update = datetime.now(timezone.utc)

                    await asyncio.sleep(interval_sec)

                except Exception as e:
                    logger.error(f"Error in OHLCV streaming loop: {e}")
                    await asyncio.sleep(interval_sec)

        except asyncio.CancelledError:
            logger.debug("OHLCV streaming cancelled", subscription_id=subscription.subscription_id)
        except Exception as e:
            logger.error(f"Fatal error in OHLCV streaming: {e}")

    async def _stream_multi_asset(self, subscription: Subscription) -> None:
        """
        Stream multiple assets simultaneously

        Similar to price streaming but optimized for multiple assets
        """
        # For now, use the same logic as price streaming
        await self._stream_prices(subscription)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
