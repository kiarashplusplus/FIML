"""
Watchdog Orchestrator

Manages the lifecycle of all watchdogs, coordinates event handling,
and provides centralized monitoring and control.
"""

import asyncio
from typing import Dict, List, Optional

from fiml.core.logging import get_logger
from fiml.watchdog.base import BaseWatchdog
from fiml.watchdog.detectors import (
    CorrelationBreakdownWatchdog,
    EarningsAnomalyWatchdog,
    ExchangeOutageWatchdog,
    FundingRateWatchdog,
    LiquidityDropWatchdog,
    PriceAnomalyWatchdog,
    UnusualVolumeWatchdog,
    WhaleMovementWatchdog,
)
from fiml.watchdog.events import EventStream
from fiml.watchdog.models import EventFilter, Severity, WatchdogEvent, WatchdogHealth

logger = get_logger(__name__)


class WatchdogManager:
    """
    Orchestrates all watchdogs

    Features:
    - Lifecycle management (startup/shutdown)
    - Health monitoring
    - Event aggregation and routing
    - Priority-based event handling
    - Configuration management
    """

    def __init__(
        self,
        event_stream: Optional[EventStream] = None,
        config: Optional[Dict] = None,
    ):
        """
        Initialize watchdog manager

        Args:
            event_stream: Event stream for events (uses global if None)
            config: Configuration dict for watchdogs
        """
        self._event_stream = event_stream
        self._config = config or self._default_config()

        # Watchdogs registry
        self._watchdogs: Dict[str, BaseWatchdog] = {}

        # Manager state
        self._initialized = False
        self._running = False

        # Event handling
        self._priority_handlers: Dict[Severity, List] = {
            Severity.CRITICAL: [],
            Severity.HIGH: [],
            Severity.MEDIUM: [],
            Severity.LOW: [],
        }

    @property
    def event_stream(self) -> EventStream:
        """Get event stream, lazy-loading from global if needed"""
        if self._event_stream is None:
            from fiml.watchdog.events import event_stream
            self._event_stream = event_stream
        return self._event_stream

    @staticmethod
    def _default_config() -> Dict:
        """Default configuration for watchdogs (loads from settings)"""
        from fiml.core.config import settings
        
        return {
            "earnings_anomaly": {
                "enabled": settings.enable_earnings_anomaly_watchdog,
                "check_interval": settings.earnings_anomaly_check_interval,
                "thresholds": {
                    "surprise_pct": settings.earnings_surprise_threshold_pct,
                },
            },
            "unusual_volume": {
                "enabled": settings.enable_unusual_volume_watchdog,
                "check_interval": settings.unusual_volume_check_interval,
                "thresholds": {
                    "volume_multiplier": settings.unusual_volume_multiplier,
                },
            },
            "whale_movement": {
                "enabled": settings.enable_whale_movement_watchdog,
                "check_interval": settings.whale_movement_check_interval,
                "thresholds": {
                    "min_usd": settings.whale_movement_min_usd,
                },
            },
            "funding_rate": {
                "enabled": settings.enable_funding_rate_watchdog,
                "check_interval": settings.funding_rate_check_interval,
                "thresholds": {
                    "rate_pct": settings.funding_rate_threshold_pct,
                },
            },
            "liquidity_drop": {
                "enabled": settings.enable_liquidity_drop_watchdog,
                "check_interval": settings.liquidity_drop_check_interval,
                "thresholds": {
                    "drop_pct": settings.liquidity_drop_threshold_pct,
                },
            },
            "correlation_breakdown": {
                "enabled": settings.enable_correlation_breakdown_watchdog,
                "check_interval": settings.correlation_breakdown_check_interval,
                "thresholds": {
                    "change_threshold": settings.correlation_change_threshold,
                },
            },
            "exchange_outage": {
                "enabled": settings.enable_exchange_outage_watchdog,
                "check_interval": settings.exchange_outage_check_interval,
            },
            "price_anomaly": {
                "enabled": settings.enable_price_anomaly_watchdog,
                "check_interval": settings.price_anomaly_check_interval,
                "thresholds": {
                    "price_change_pct": settings.price_anomaly_threshold_pct,
                },
            },
            # Global settings
            "global": {
                "enabled": settings.watchdog_global_enabled,
                "event_stream_enabled": settings.watchdog_event_stream_enabled,
                "event_persistence": settings.watchdog_event_persistence,
                "websocket_broadcast": settings.watchdog_websocket_broadcast,
                "max_events_in_memory": settings.watchdog_max_events_in_memory,
                "health_check_interval": settings.watchdog_health_check_interval,
            },
        }

    async def initialize(self) -> None:
        """Initialize the watchdog system"""
        if self._initialized:
            logger.warning("Watchdog manager already initialized")
            return

        logger.info("Initializing watchdog manager")

        # Initialize event stream
        await self.event_stream.initialize()

        # Register all watchdogs
        await self._register_watchdogs()

        # Subscribe to high-priority events
        self._setup_priority_handlers()

        self._initialized = True
        logger.info(f"Watchdog manager initialized with {len(self._watchdogs)} watchdogs")

    async def _register_watchdogs(self) -> None:
        """Register all watchdog instances"""
        watchdog_classes = [
            EarningsAnomalyWatchdog,
            UnusualVolumeWatchdog,
            WhaleMovementWatchdog,
            FundingRateWatchdog,
            LiquidityDropWatchdog,
            CorrelationBreakdownWatchdog,
            ExchangeOutageWatchdog,
            PriceAnomalyWatchdog,
        ]

        for watchdog_class in watchdog_classes:
            try:
                # Get config for this watchdog
                watchdog_name = watchdog_class.__name__.replace("Watchdog", "").lower()
                # Convert CamelCase to snake_case
                watchdog_name = self._camel_to_snake(watchdog_name)

                config = self._config.get(watchdog_name, {})

                # Create instance
                watchdog = watchdog_class(
                    check_interval=config.get("check_interval", 60),
                    enabled=config.get("enabled", True),
                )

                # Set event stream
                watchdog.set_event_stream(self._event_stream)

                # Register
                self._watchdogs[watchdog.name] = watchdog
                logger.info(f"Registered watchdog: {watchdog.name}")

            except Exception as e:
                logger.error(f"Failed to register watchdog {watchdog_class.__name__}: {e}")

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def _setup_priority_handlers(self) -> None:
        """Setup handlers for high-priority events"""
        # Subscribe to critical events
        self._event_stream.subscribe(
            callback=self._handle_critical_event,
            event_filter=EventFilter(severities=[Severity.CRITICAL]),
            subscriber_id="manager_critical",
        )

        # Subscribe to high-priority events
        self._event_stream.subscribe(
            callback=self._handle_high_priority_event,
            event_filter=EventFilter(severities=[Severity.HIGH]),
            subscriber_id="manager_high",
        )

    async def _handle_critical_event(self, event: WatchdogEvent) -> None:
        """Handle critical events with immediate action"""
        logger.critical(
            f"CRITICAL EVENT: {event.description} "
            f"(type={event.type.value}, asset={event.asset.symbol if event.asset else 'N/A'})"
        )

        # In production, this could:
        # - Send alerts to operations team
        # - Trigger circuit breakers
        # - Execute emergency protocols

    async def _handle_high_priority_event(self, event: WatchdogEvent) -> None:
        """Handle high-priority events"""
        logger.warning(
            f"HIGH PRIORITY EVENT: {event.description} "
            f"(type={event.type.value}, asset={event.asset.symbol if event.asset else 'N/A'})"
        )

        # In production, could trigger automated responses

    async def start(self) -> None:
        """Start all enabled watchdogs"""
        if not self._initialized:
            await self.initialize()

        if self._running:
            logger.warning("Watchdog manager already running")
            return

        logger.info("Starting watchdog manager")
        self._running = True

        # Start all watchdogs
        start_tasks = []
        for watchdog in self._watchdogs.values():
            if watchdog.enabled:
                start_tasks.append(watchdog.start())

        await asyncio.gather(*start_tasks, return_exceptions=True)

        logger.info(f"Started {len(start_tasks)} watchdogs")

    async def stop(self) -> None:
        """Stop all watchdogs gracefully"""
        if not self._running:
            return

        logger.info("Stopping watchdog manager")
        self._running = False

        # Stop all watchdogs
        stop_tasks = []
        for watchdog in self._watchdogs.values():
            if watchdog.is_running():
                stop_tasks.append(watchdog.stop())

        await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Shutdown event stream
        await self._event_stream.shutdown()

        logger.info("Watchdog manager stopped")

    async def restart_watchdog(self, name: str) -> bool:
        """
        Restart a specific watchdog

        Args:
            name: Watchdog name

        Returns:
            True if restarted successfully
        """
        watchdog = self._watchdogs.get(name)
        if not watchdog:
            logger.error(f"Watchdog not found: {name}")
            return False

        try:
            logger.info(f"Restarting watchdog: {name}")
            await watchdog.stop()
            await asyncio.sleep(1)  # Brief pause
            await watchdog.start()
            return True
        except Exception as e:
            logger.error(f"Failed to restart watchdog {name}: {e}")
            return False

    def get_health(self) -> Dict[str, WatchdogHealth]:
        """Get health status of all watchdogs"""
        return {
            name: watchdog.get_health()
            for name, watchdog in self._watchdogs.items()
        }

    def get_watchdog(self, name: str) -> Optional[BaseWatchdog]:
        """Get watchdog by name"""
        return self._watchdogs.get(name)

    def list_watchdogs(self) -> List[str]:
        """List all registered watchdog names"""
        return list(self._watchdogs.keys())

    async def enable_watchdog(self, name: str) -> bool:
        """Enable and start a watchdog"""
        watchdog = self._watchdogs.get(name)
        if not watchdog:
            return False

        watchdog.enabled = True
        if self._running:
            await watchdog.start()
        return True

    async def disable_watchdog(self, name: str) -> bool:
        """Disable and stop a watchdog"""
        watchdog = self._watchdogs.get(name)
        if not watchdog:
            return False

        watchdog.enabled = False
        await watchdog.stop()
        return True

    def get_event_stats(self) -> Dict:
        """Get event stream statistics"""
        return self._event_stream.get_stats()

    def get_recent_events(
        self,
        event_filter: Optional[EventFilter] = None,
        limit: int = 100,
    ) -> List[WatchdogEvent]:
        """Get recent events from event stream"""
        return self._event_stream.get_history(event_filter=event_filter, limit=limit)

    def subscribe_to_events(
        self,
        callback,
        event_filter: Optional[EventFilter] = None,
    ) -> str:
        """
        Subscribe to events

        Args:
            callback: Callback function for events
            event_filter: Filter for events

        Returns:
            Subscription ID
        """
        return self._event_stream.subscribe(callback=callback, event_filter=event_filter)

    def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        return self._event_stream.unsubscribe(subscription_id)

    def get_status(self) -> Dict:
        """Get overall manager status"""
        health = self.get_health()

        healthy = sum(1 for h in health.values() if h.status == "healthy")
        degraded = sum(1 for h in health.values() if h.status == "degraded")
        unhealthy = sum(1 for h in health.values() if h.status == "unhealthy")

        return {
            "initialized": self._initialized,
            "running": self._running,
            "total_watchdogs": len(self._watchdogs),
            "enabled_watchdogs": sum(1 for w in self._watchdogs.values() if w.enabled),
            "running_watchdogs": sum(1 for w in self._watchdogs.values() if w.is_running()),
            "health_summary": {
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
            },
            "event_stats": self.get_event_stats(),
        }


# Global watchdog manager instance
watchdog_manager = WatchdogManager()
