"""
Real-time Dashboard

Provides HTTP endpoints and WebSocket streaming for real-time monitoring
of watchdog events, multi-asset data, and system health.

Features:
- WebSocket streaming for live updates
- Watchdog event display
- Multi-asset monitoring
- System health metrics
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, Market
from fiml.watchdog.models import EventFilter, EventType, Severity, WatchdogEvent
from fiml.watchdog.orchestrator import watchdog_manager
from fiml.websocket.manager import websocket_manager

logger = get_logger(__name__)

# Create router
dashboard_router = APIRouter()


# Models for dashboard API
class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_events: int
    events_by_severity: Dict[str, int]
    active_watchdogs: int
    healthy_watchdogs: int
    active_subscriptions: int
    timestamp: datetime


class WatchdogStatus(BaseModel):
    """Watchdog health status"""
    name: str
    enabled: bool
    running: bool
    status: str
    last_check: Optional[datetime]
    consecutive_failures: int
    total_checks: int


class MultiAssetData(BaseModel):
    """Multi-asset monitoring data"""
    symbol: str
    asset_type: str
    price: Optional[float]
    change_percent: Optional[float]
    volume: Optional[float]
    timestamp: datetime


# HTTP Endpoints
@dashboard_router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """
    Get overall dashboard statistics

    Returns real-time stats about events, watchdogs, and active connections.
    """
    event_stats = watchdog_manager.get_event_stats()
    status = watchdog_manager.get_status()

    return DashboardStats(
        total_events=event_stats.get("total_events", 0),
        events_by_severity=event_stats.get("events_by_severity", {}),
        active_watchdogs=status.get("enabled_watchdogs", 0),
        healthy_watchdogs=status["health_summary"].get("healthy", 0),
        active_subscriptions=len(websocket_manager.active_connections),
        timestamp=datetime.now(timezone.utc),
    )


@dashboard_router.get("/watchdogs", response_model=List[WatchdogStatus])
async def get_watchdog_status() -> List[WatchdogStatus]:
    """
    Get status of all watchdogs

    Returns detailed health information for each watchdog.
    """
    health_data = watchdog_manager.get_health()

    watchdog_statuses = []
    for name, health in health_data.items():
        watchdog = watchdog_manager.get_watchdog(name)
        if watchdog:
            watchdog_statuses.append(
                WatchdogStatus(
                    name=name,
                    enabled=watchdog.enabled,
                    running=watchdog.is_running(),
                    status=health.status,
                    last_check=health.last_check,
                    consecutive_failures=health.consecutive_failures,
                    total_checks=health.total_checks,
                )
            )

    return watchdog_statuses


@dashboard_router.get("/events", response_model=List[WatchdogEvent])
async def get_recent_events(
    limit: int = Query(default=100, ge=1, le=1000),
    severity: Optional[Severity] = None,
    event_type: Optional[str] = None,
) -> List[WatchdogEvent]:
    """
    Get recent watchdog events

    Args:
        limit: Maximum number of events to return (1-1000)
        severity: Filter by severity level
        event_type: Filter by event type

    Returns:
        List of recent watchdog events
    """
    event_filter = None
    if severity or event_type:
        # Convert string event_type to EventType enum if provided
        event_types_list = None
        if event_type:
            try:
                event_types_list = [EventType(event_type)]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type: {event_type}"
                )

        event_filter = EventFilter(
            severities=[severity] if severity else None,
            event_types=event_types_list,
        )

    events = watchdog_manager.get_recent_events(
        event_filter=event_filter,
        limit=limit,
    )

    return events


@dashboard_router.post("/watchdogs/{name}/enable")
async def enable_watchdog(name: str) -> Dict:
    """
    Enable a specific watchdog

    Args:
        name: Watchdog name

    Returns:
        Success status
    """
    success = await watchdog_manager.enable_watchdog(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Watchdog '{name}' not found")

    return {"status": "enabled", "watchdog": name}


@dashboard_router.post("/watchdogs/{name}/disable")
async def disable_watchdog(name: str) -> Dict:
    """
    Disable a specific watchdog

    Args:
        name: Watchdog name

    Returns:
        Success status
    """
    success = await watchdog_manager.disable_watchdog(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Watchdog '{name}' not found")

    return {"status": "disabled", "watchdog": name}


@dashboard_router.post("/watchdogs/{name}/restart")
async def restart_watchdog(name: str) -> Dict:
    """
    Restart a specific watchdog

    Args:
        name: Watchdog name

    Returns:
        Success status
    """
    success = await watchdog_manager.restart_watchdog(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Watchdog '{name}' not found")

    return {"status": "restarted", "watchdog": name}


# WebSocket Endpoint for Real-time Dashboard Updates
@dashboard_router.websocket("/stream")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates

    Streams:
    - Watchdog events as they occur
    - System health updates
    - Asset price updates

    Message format:
    {
        "type": "event" | "health" | "stats",
        "data": {...}
    }
    """
    await websocket.accept()
    connection_id = f"dashboard_{datetime.now(timezone.utc).timestamp()}"

    logger.info("Dashboard WebSocket connected", connection_id=connection_id)

    # Subscribe to watchdog events
    subscription_id = None

    try:
        # Subscribe to all watchdog events
        def event_callback(event: WatchdogEvent):
            """Callback for watchdog events - creates async task"""
            async def send_event():
                try:
                    await websocket.send_json({
                        "type": "event",
                        "data": event.to_dict(),
                    })
                except Exception as e:
                    logger.error(f"Error sending event to dashboard: {e}")

            asyncio.create_task(send_event())

        subscription_id = watchdog_manager.subscribe_to_events(
            callback=event_callback,
            event_filter=None,  # Subscribe to all events
        )

        # Send initial stats
        stats = await get_dashboard_stats()
        await websocket.send_json({
            "type": "stats",
            "data": stats.model_dump(mode="json"),
        })

        # Keep connection alive and send periodic updates
        while True:
            try:
                # Wait for client messages (e.g., ping)
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send periodic stats update
                stats = await get_dashboard_stats()
                await websocket.send_json({
                    "type": "stats",
                    "data": stats.model_dump(mode="json"),
                })

    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected", connection_id=connection_id)
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}", connection_id=connection_id)
    finally:
        # Unsubscribe from events
        if subscription_id:
            watchdog_manager.unsubscribe_from_events(subscription_id)


@dashboard_router.get("/assets/monitor")
async def get_monitored_assets(
    symbols: List[str] = Query(..., description="List of symbols to monitor"),
    asset_type: AssetType = Query(default=AssetType.EQUITY),
    market: Market = Query(default=Market.US),
) -> List[MultiAssetData]:
    """
    Get current data for multiple assets

    Args:
        symbols: List of asset symbols
        asset_type: Type of assets
        market: Market for the assets

    Returns:
        Current data for each asset
    """
    from fiml.arbitration.engine import arbitration_engine
    from fiml.core.models import DataType

    results = []

    for symbol in symbols:
        try:
            asset = Asset(
                symbol=symbol,
                asset_type=asset_type,
                market=market,
            )

            # Get price data
            plan = await arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.PRICE,
                user_region="US",
            )

            response = await arbitration_engine.execute_with_fallback(
                plan=plan,
                asset=asset,
                data_type=DataType.PRICE,
            )

            price_data = response.data

            results.append(
                MultiAssetData(
                    symbol=symbol,
                    asset_type=asset_type.value,
                    price=price_data.get("price"),
                    change_percent=price_data.get("change_percent"),
                    volume=price_data.get("volume"),
                    timestamp=response.timestamp,
                )
            )

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            # Add placeholder data for failed fetch
            results.append(
                MultiAssetData(
                    symbol=symbol,
                    asset_type=asset_type.value,
                    price=None,
                    change_percent=None,
                    volume=None,
                    timestamp=datetime.now(timezone.utc),
                )
            )

    return results
