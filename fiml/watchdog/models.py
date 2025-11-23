"""
Watchdog Event Models

Defines the event types, severity levels, and data structures
for the real-time event intelligence system.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from fiml.core.models import Asset


class EventType(str, Enum):
    """Types of watchdog events"""

    # Earnings and fundamentals
    EARNINGS_ANOMALY = "earnings_anomaly"

    # Volume and trading activity
    UNUSUAL_VOLUME = "unusual_volume"

    # Crypto-specific
    WHALE_MOVEMENT = "whale_movement"
    FUNDING_SPIKE = "funding_spike"
    LIQUIDITY_DROP = "liquidity_drop"

    # Cross-asset
    CORRELATION_BREAK = "correlation_break"

    # Infrastructure
    EXCHANGE_OUTAGE = "exchange_outage"

    # Price movements
    PRICE_ANOMALY = "price_anomaly"
    FLASH_CRASH = "flash_crash"
    ARBITRAGE_OPPORTUNITY = "arbitrage_opportunity"


class Severity(str, Enum):
    """Event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WatchdogEvent(BaseModel):
    """
    Structured event emitted by watchdogs

    Attributes:
        event_id: Unique event identifier
        type: Type of event
        severity: Event severity level
        asset: Associated asset (optional for infrastructure events)
        description: Human-readable description
        data: Event-specific data payload
        timestamp: Event creation time
        watchdog: Name of watchdog that generated the event
        metadata: Additional metadata
    """

    event_id: str = Field(default_factory=lambda: f"evt_{datetime.now(timezone.utc).timestamp()}")
    type: EventType
    severity: Severity
    asset: Optional[Asset] = None
    description: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    watchdog: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "severity": self.severity.value,
            "asset": self.asset.model_dump() if self.asset else None,
            "description": self.description,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "watchdog": self.watchdog,
            "metadata": self.metadata,
        }


class EventFilter(BaseModel):
    """
    Filter for subscribing to specific events

    Attributes:
        event_types: Filter by event types (None = all)
        severities: Filter by severities (None = all)
        assets: Filter by assets (None = all)
        watchdogs: Filter by watchdog names (None = all)
    """

    event_types: Optional[list[EventType]] = None
    severities: Optional[list[Severity]] = None
    assets: Optional[list[str]] = None  # Asset symbols
    watchdogs: Optional[list[str]] = None

    def matches(self, event: WatchdogEvent) -> bool:
        """Check if event matches this filter"""

        if self.event_types and event.type not in self.event_types:
            return False

        if self.severities and event.severity not in self.severities:
            return False

        if self.assets and event.asset:
            if event.asset.symbol not in self.assets:
                return False

        if self.watchdogs and event.watchdog not in self.watchdogs:
            return False

        return True


class WatchdogHealth(BaseModel):
    """
    Health status of a watchdog

    Attributes:
        name: Watchdog name
        status: Current status (healthy, degraded, unhealthy)
        last_check: Last successful check time
        last_event: Last event emission time
        events_emitted: Total events emitted
        errors: Recent error count
        uptime_seconds: Uptime in seconds
        metadata: Additional health info
    """

    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    last_check: Optional[datetime] = None
    last_event: Optional[datetime] = None
    events_emitted: int = 0
    errors: int = 0
    uptime_seconds: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_event": self.last_event.isoformat() if self.last_event else None,
            "events_emitted": self.events_emitted,
            "errors": self.errors,
            "uptime_seconds": self.uptime_seconds,
            "metadata": self.metadata,
        }
