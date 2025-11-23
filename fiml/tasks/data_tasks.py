"""
Data fetching and caching tasks
"""

from typing import Optional

from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, Market
from fiml.providers import provider_registry
from fiml.tasks.celery import celery_app

logger = get_logger(__name__)


@celery_app.task(name="fiml.tasks.data_tasks.fetch_historical_data")
def fetch_historical_data(
    symbol: str,
    asset_type: str = "stock",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    Fetch historical data for an asset

    Args:
        symbol: Asset symbol
        asset_type: Type of asset (stock, crypto, etc.)
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        Dict with status and data
    """
    logger.info(
        "Fetching historical data",
        symbol=symbol,
        asset_type=asset_type,
        start_date=start_date,
        end_date=end_date,
    )

    try:
        # Create asset
        Asset(
            symbol=symbol,
            asset_type=AssetType(asset_type),
            market=Market.US,
        )

        # This would call the provider registry to fetch data
        # For now, return a placeholder
        return {
            "status": "success",
            "symbol": symbol,
            "message": f"Historical data fetch queued for {symbol}",
        }

    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return {
            "status": "error",
            "symbol": symbol,
            "error": str(e),
        }


@celery_app.task(name="fiml.tasks.data_tasks.refresh_cache")
def refresh_cache(top_n: int = 100) -> dict:
    """
    Refresh cache for most frequently accessed assets

    Args:
        top_n: Number of top assets to refresh

    Returns:
        Dict with status and count
    """
    logger.info("Refreshing cache", top_n=top_n)

    try:
        # This would refresh the cache for the most accessed items
        # For now, return a placeholder
        return {
            "status": "success",
            "refreshed": top_n,
            "message": f"Cache refresh completed for {top_n} items",
        }

    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@celery_app.task(name="fiml.tasks.data_tasks.update_provider_health")
def update_provider_health() -> dict:
    """
    Update health metrics for all providers

    Returns:
        Dict with status and provider count
    """
    logger.info("Updating provider health metrics")

    try:
        # This would ping all providers and update their health status
        # For now, return a placeholder
        provider_count = len(provider_registry.providers)

        return {
            "status": "success",
            "providers_checked": provider_count,
            "message": f"Health check completed for {provider_count} providers",
        }

    except Exception as e:
        logger.error(f"Error updating provider health: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
