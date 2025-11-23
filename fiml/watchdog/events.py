"""
Event Stream Manager

Manages event publishing, subscription, persistence, and broadcasting
for the watchdog event intelligence system.
"""

import asyncio
import contextlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from fiml.core.logging import get_logger
from fiml.watchdog.models import EventFilter, WatchdogEvent

logger = get_logger(__name__)


class EventStream:
    """
    Event stream for publishing and subscribing to watchdog events

    Features:
    - Pub/sub event distribution
    - Event filtering and routing
    - Persistence to Redis Streams (if available)
    - WebSocket broadcasting
    - Event history tracking
    """

    def __init__(
        self,
        max_history: int = 1000,
        enable_persistence: bool = True,
        enable_websocket: bool = True,
    ):
        """
        Initialize event stream

        Args:
            max_history: Maximum events to keep in memory
            enable_persistence: Enable Redis Streams persistence
            enable_websocket: Enable WebSocket broadcasting
        """
        self.max_history = max_history
        self.enable_persistence = enable_persistence
        self.enable_websocket = enable_websocket

        # Subscribers: {subscriber_id: (filter, callback)}
        self._subscribers: Dict[str, tuple[EventFilter, Callable]] = {}

        # Event history (in-memory circular buffer)
        self._event_history: List[WatchdogEvent] = []

        # Event stats
        self._total_events = 0
        self._events_by_type: Dict[str, int] = defaultdict(int)
        self._events_by_severity: Dict[str, int] = defaultdict(int)

        # Redis client (optional)
        self._redis_client = None

        # WebSocket manager (optional)
        self._websocket_manager = None

        # Background tasks
        self._tasks: List[asyncio.Task] = []

    async def initialize(self) -> None:
        """Initialize event stream components"""
        logger.info("Initializing event stream")

        # Initialize Redis if persistence enabled
        if self.enable_persistence:
            await self._init_redis()

        # Initialize WebSocket if broadcasting enabled
        if self.enable_websocket:
            await self._init_websocket()

        logger.info("Event stream initialized")

    async def _init_redis(self) -> None:
        """Initialize Redis connection for persistence"""
        try:
            from fiml.cache.l1_cache import l1_cache

            # Reuse L1 cache Redis connection
            if l1_cache._client:
                self._redis_client = l1_cache._client
                logger.info("Event stream using L1 cache Redis client")
            else:
                logger.warning("Redis not available for event persistence")
                self.enable_persistence = False
        except Exception as e:
            logger.warning(f"Failed to initialize Redis for event stream: {e}")
            self.enable_persistence = False

    async def _init_websocket(self) -> None:
        """Initialize WebSocket manager for broadcasting"""
        try:

            # For now, we'll create a reference point
            # In production, this would be injected
            self._websocket_manager = None  # Will be set by server
            logger.info("Event stream WebSocket broadcasting ready")
        except Exception as e:
            logger.warning(f"WebSocket not available for event broadcasting: {e}")
            self.enable_websocket = False

    def set_websocket_manager(self, manager) -> None:
        """Set WebSocket manager for broadcasting"""
        self._websocket_manager = manager
        logger.info("WebSocket manager configured for event stream")

    async def emit(self, event: WatchdogEvent) -> None:
        """
        Emit an event to all subscribers and persistence layers

        Args:
            event: Watchdog event to emit
        """
        logger.debug(f"Emitting event: {event.type.value} (severity: {event.severity.value})")

        # Update stats
        self._total_events += 1
        self._events_by_type[event.type.value] += 1
        self._events_by_severity[event.severity.value] += 1

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self.max_history:
            self._event_history.pop(0)

        # Persist to Redis
        if self.enable_persistence and self._redis_client:
            await self._persist_to_redis(event)

        # Broadcast via WebSocket
        if self.enable_websocket and self._websocket_manager:
            await self._broadcast_to_websocket(event)

        # Notify subscribers
        await self._notify_subscribers(event)

    async def _persist_to_redis(self, event: WatchdogEvent) -> None:
        """Persist event to Redis Streams"""
        try:
            stream_name = "watchdog:events"

            # Serialize event
            event_data = event.to_dict()

            # Add to Redis Stream
            await self._redis_client.xadd(
                stream_name,
                event_data,
                maxlen=10000  # Keep last 10k events
            )

            logger.debug(f"Event persisted to Redis stream: {stream_name}")
        except Exception as e:
            logger.error(f"Failed to persist event to Redis: {e}")

    async def _broadcast_to_websocket(self, event: WatchdogEvent) -> None:
        """Broadcast event to WebSocket clients"""
        try:
            if not self._websocket_manager:
                return

            # Format as WebSocket message
            message = {
                "type": "watchdog_event",
                "event": event.to_dict(),
            }

            # Broadcast to all connected clients
            # In production, this would filter by client subscriptions
            await self._websocket_manager.broadcast(message)

            logger.debug("Event broadcasted via WebSocket")
        except Exception as e:
            logger.error(f"Failed to broadcast event via WebSocket: {e}")

    async def _notify_subscribers(self, event: WatchdogEvent) -> None:
        """Notify matching subscribers"""
        for subscriber_id, (event_filter, callback) in self._subscribers.items():
            try:
                # Check if event matches filter
                if event_filter.matches(event):
                    # Call subscriber callback
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
            except Exception as e:
                logger.error(
                    f"Error notifying subscriber {subscriber_id}: {e}",
                    exc_info=True
                )

    def subscribe(
        self,
        callback: Callable,
        event_filter: Optional[EventFilter] = None,
        subscriber_id: Optional[str] = None,
    ) -> str:
        """
        Subscribe to events

        Args:
            callback: Function to call on matching events
            event_filter: Filter for events (None = all events)
            subscriber_id: Optional custom subscriber ID

        Returns:
            Subscriber ID for unsubscribing
        """
        if subscriber_id is None:
            subscriber_id = f"sub_{len(self._subscribers)}_{datetime.now(timezone.utc).timestamp()}"

        if event_filter is None:
            event_filter = EventFilter()  # Match all events

        self._subscribers[subscriber_id] = (event_filter, callback)
        logger.info(f"New subscriber: {subscriber_id}")

        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        Unsubscribe from events

        Args:
            subscriber_id: Subscriber ID to remove

        Returns:
            True if unsubscribed, False if not found
        """
        if subscriber_id in self._subscribers:
            del self._subscribers[subscriber_id]
            logger.info(f"Unsubscribed: {subscriber_id}")
            return True
        return False

    def get_history(
        self,
        event_filter: Optional[EventFilter] = None,
        limit: int = 100,
    ) -> List[WatchdogEvent]:
        """
        Get event history

        Args:
            event_filter: Filter for events
            limit: Maximum events to return

        Returns:
            List of events (newest first)
        """
        events = self._event_history[::-1]  # Reverse for newest first

        if event_filter:
            events = [e for e in events if event_filter.matches(e)]

        return events[:limit]

    async def get_persisted_events(
        self,
        start_id: str = "-",
        count: int = 100,
    ) -> List[WatchdogEvent]:
        """
        Get persisted events from Redis Streams

        Args:
            start_id: Redis Stream ID to start from
            count: Maximum events to retrieve

        Returns:
            List of events
        """
        if not self._redis_client:
            return []

        try:
            stream_name = "watchdog:events"

            # Read from Redis Stream
            results = await self._redis_client.xread(
                {stream_name: start_id},
                count=count
            )

            events = []
            for stream, messages in results:
                for msg_id, data in messages:
                    # Deserialize event
                    # Note: This is simplified - full implementation would properly reconstruct WatchdogEvent
                    events.append(data)

            return events
        except Exception as e:
            logger.error(f"Failed to read persisted events: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get event stream statistics"""
        return {
            "total_events": self._total_events,
            "events_by_type": dict(self._events_by_type),
            "events_by_severity": dict(self._events_by_severity),
            "active_subscribers": len(self._subscribers),
            "history_size": len(self._event_history),
            "persistence_enabled": self.enable_persistence,
            "websocket_enabled": self.enable_websocket,
        }

    async def shutdown(self) -> None:
        """Shutdown event stream"""
        logger.info("Shutting down event stream")

        # Cancel background tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        # Clear subscribers
        self._subscribers.clear()

        logger.info("Event stream shutdown complete")


# Global event stream instance
event_stream = EventStream()
