"""
Alert API Router

Provides REST API endpoints for managing custom alerts.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from fiml.alerts.builder import (
    AlertConfig,
    AlertTrigger,
    DeliveryMethod,
    EmailConfig,
    TelegramConfig,
    WebhookConfig,
    alert_builder,
)
from fiml.core.logging import get_logger

logger = get_logger(__name__)

# Create router
alert_router = APIRouter()


@alert_router.post("/alerts", response_model=AlertConfig)
async def create_alert(config: AlertConfig) -> AlertConfig:
    """
    Create a new alert
    
    Args:
        config: Alert configuration
    
    Returns:
        Created alert configuration
    """
    # Ensure alert builder is initialized
    if not alert_builder._initialized:
        await alert_builder.initialize()
    
    try:
        return alert_builder.create_alert(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@alert_router.get("/alerts", response_model=List[AlertConfig])
async def list_alerts(
    enabled_only: bool = Query(default=False, description="Only return enabled alerts")
) -> List[AlertConfig]:
    """
    List all alerts
    
    Args:
        enabled_only: Filter to only enabled alerts
    
    Returns:
        List of alert configurations
    """
    return alert_builder.list_alerts(enabled_only=enabled_only)


@alert_router.get("/alerts/{alert_id}", response_model=AlertConfig)
async def get_alert(alert_id: str) -> AlertConfig:
    """
    Get alert by ID
    
    Args:
        alert_id: Alert ID
    
    Returns:
        Alert configuration
    """
    config = alert_builder.get_alert(alert_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return config


@alert_router.put("/alerts/{alert_id}", response_model=AlertConfig)
async def update_alert(alert_id: str, config: AlertConfig) -> AlertConfig:
    """
    Update an existing alert
    
    Args:
        alert_id: Alert ID to update
        config: New alert configuration
    
    Returns:
        Updated alert configuration
    """
    try:
        return alert_builder.update_alert(alert_id, config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@alert_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str) -> dict:
    """
    Delete an alert
    
    Args:
        alert_id: Alert ID to delete
    
    Returns:
        Success status
    """
    success = alert_builder.delete_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    
    return {"status": "deleted", "alert_id": alert_id}


@alert_router.post("/alerts/{alert_id}/enable")
async def enable_alert(alert_id: str) -> dict:
    """
    Enable an alert
    
    Args:
        alert_id: Alert ID to enable
    
    Returns:
        Success status
    """
    config = alert_builder.get_alert(alert_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    
    config.enabled = True
    alert_builder.update_alert(alert_id, config)
    
    return {"status": "enabled", "alert_id": alert_id}


@alert_router.post("/alerts/{alert_id}/disable")
async def disable_alert(alert_id: str) -> dict:
    """
    Disable an alert
    
    Args:
        alert_id: Alert ID to disable
    
    Returns:
        Success status
    """
    config = alert_builder.get_alert(alert_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    
    config.enabled = False
    alert_builder.update_alert(alert_id, config)
    
    return {"status": "disabled", "alert_id": alert_id}
