"""
FIML - Financial Intelligence Meta-Layer
AI-Native Multi-Market Financial Intelligence Framework
"""

__version__ = "0.3.0"
__author__ = "Kiarash Adl"
__license__ = "Apache-2.0"

from fiml.core.config import settings

# Watchdog event intelligence system
from fiml.watchdog import (
    EventFilter,
    EventStream,
    EventType,
    Severity,
    WatchdogEvent,
    WatchdogManager,
    event_stream,
    watchdog_manager,
)

__all__ = [
    "settings",
    # Watchdog components
    "WatchdogManager",
    "EventStream",
    "WatchdogEvent",
    "EventType",
    "Severity",
    "EventFilter",
    "watchdog_manager",
    "event_stream",
]
