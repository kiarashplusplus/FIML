"""
Watchdog - Real-time Event Intelligence System

Monitors markets for anomalies, unusual activity, and significant events
in real-time with automated detection and alerting.

Components:
- BaseWatchdog: Abstract base class for all watchdogs
- 8 Specialized Detectors: Earnings, Volume, Whale, Funding, Liquidity, Correlation, Exchange, Price
- EventStream: Pub/sub event distribution with persistence
- WatchdogManager: Orchestrator for lifecycle and coordination
- Models: Event types, severity levels, filters, and health tracking

Usage:
    from fiml.watchdog import watchdog_manager

    # Initialize and start
    await watchdog_manager.initialize()
    await watchdog_manager.start()

    # Subscribe to events
    def handle_event(event):
        print(f"Event: {event.description}")

    subscription_id = watchdog_manager.subscribe_to_events(
        callback=handle_event,
        event_filter=EventFilter(severities=[Severity.HIGH, Severity.CRITICAL])
    )

    # Get health status
    health = watchdog_manager.get_health()

    # Stop
    await watchdog_manager.stop()
"""

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
from fiml.watchdog.events import EventStream, event_stream
from fiml.watchdog.models import EventFilter, EventType, Severity, WatchdogEvent, WatchdogHealth
from fiml.watchdog.orchestrator import WatchdogManager, watchdog_manager

__all__ = [
    # Core classes
    "BaseWatchdog",
    "EventStream",
    "WatchdogManager",
    # Detectors
    "EarningsAnomalyWatchdog",
    "UnusualVolumeWatchdog",
    "WhaleMovementWatchdog",
    "FundingRateWatchdog",
    "LiquidityDropWatchdog",
    "CorrelationBreakdownWatchdog",
    "ExchangeOutageWatchdog",
    "PriceAnomalyWatchdog",
    # Models
    "WatchdogEvent",
    "EventType",
    "Severity",
    "EventFilter",
    "WatchdogHealth",
    # Global instances
    "event_stream",
    "watchdog_manager",
]
