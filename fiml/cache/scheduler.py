"""
Batch Update Scheduler - Groups and schedules cache updates
Reduces API calls by batching similar requests during low-load periods
"""

import asyncio
import contextlib
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from fiml.core.logging import get_logger
from fiml.core.models import Asset, DataType

logger = get_logger(__name__)


class UpdateRequest:
    """Represents a cache update request"""

    def __init__(
        self,
        asset: Asset,
        data_type: DataType,
        provider: str,
        priority: int = 0
    ):
        self.asset = asset
        self.data_type = data_type
        self.provider = provider
        self.priority = priority
        self.created_at = datetime.now(UTC)

    def get_batch_key(self) -> str:
        """Get key for grouping similar requests"""
        return f"{self.data_type.value}:{self.provider}"

    def __repr__(self) -> str:
        return f"UpdateRequest({self.asset.symbol}, {self.data_type.value}, {self.provider})"


class BatchUpdateScheduler:
    """
    Schedules cache updates in batches during low-load periods

    Features:
    - Groups similar requests by data type and provider
    - Schedules updates during off-peak hours
    - Batches provider API calls to reduce rate limiting
    - Updates multiple cache entries atomically
    - Configurable batch size and interval
    - Priority-based scheduling
    """

    def __init__(
        self,
        cache_manager: Any,
        provider_registry: Any,
        batch_size: int = 50,
        batch_interval_seconds: int = 60,
        low_load_hours: Optional[List[int]] = None,
        max_concurrent_batches: int = 5,
    ):
        """
        Initialize batch scheduler

        Args:
            cache_manager: Cache manager instance
            provider_registry: Provider registry for data fetching
            batch_size: Maximum requests per batch
            batch_interval_seconds: How often to process batches
            low_load_hours: Hours (0-23) considered low-load (default: 0-6)
            max_concurrent_batches: Maximum concurrent batch processing
        """
        self.cache_manager = cache_manager
        self.provider_registry = provider_registry
        self.batch_size = batch_size
        self.batch_interval_seconds = batch_interval_seconds
        self.low_load_hours = low_load_hours or list(range(0, 7))  # Midnight to 6 AM
        self.max_concurrent_batches = max_concurrent_batches

        # Pending update requests
        self.pending_requests: List[UpdateRequest] = []
        self.pending_lock = asyncio.Lock()

        # Processing state
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Statistics
        self.total_requests = 0
        self.batches_processed = 0
        self.successful_updates = 0
        self.failed_updates = 0
        self.api_calls_saved = 0

    async def schedule_update(
        self,
        asset: Asset,
        data_type: DataType,
        provider: str,
        priority: int = 0
    ) -> None:
        """
        Schedule a cache update

        Args:
            asset: Asset to update
            data_type: Type of data to update
            provider: Provider to use
            priority: Update priority (higher = sooner)
        """
        request = UpdateRequest(asset, data_type, provider, priority)

        async with self.pending_lock:
            self.pending_requests.append(request)
            self.total_requests += 1

        logger.debug(
            "Update scheduled",
            asset=asset.symbol,
            data_type=data_type.value,
            provider=provider,
            pending=len(self.pending_requests)
        )

    async def schedule_updates_batch(
        self,
        updates: List[Tuple[Asset, DataType, str, int]]
    ) -> None:
        """
        Schedule multiple updates at once

        Args:
            updates: List of (asset, data_type, provider, priority) tuples
        """
        requests = [
            UpdateRequest(asset, data_type, provider, priority)
            for asset, data_type, provider, priority in updates
        ]

        async with self.pending_lock:
            self.pending_requests.extend(requests)
            self.total_requests += len(requests)

        logger.info(
            "Batch updates scheduled",
            count=len(requests),
            pending=len(self.pending_requests)
        )

    def _group_requests_by_batch_key(
        self,
        requests: List[UpdateRequest]
    ) -> Dict[str, List[UpdateRequest]]:
        """Group requests by batch key (data_type:provider)"""
        batches: Dict[str, List[UpdateRequest]] = defaultdict(list)

        for request in requests:
            batch_key = request.get_batch_key()
            batches[batch_key].append(request)

        return dict(batches)

    def _get_next_batch(self) -> List[UpdateRequest]:
        """
        Get next batch of requests to process

        Prioritizes:
        1. High priority requests
        2. Older requests
        3. Batch size limits
        """
        if not self.pending_requests:
            return []

        # Sort by priority (desc) then age (asc)
        sorted_requests = sorted(
            self.pending_requests,
            key=lambda r: (-r.priority, r.created_at)
        )

        # Take up to batch_size requests
        batch = sorted_requests[:self.batch_size]

        return batch

    async def _process_batch(self, batch: List[UpdateRequest]) -> Dict[str, int]:
        """
        Process a batch of update requests

        Args:
            batch: List of update requests

        Returns:
            Stats dict with success/failure counts
        """
        stats = {"success": 0, "failed": 0, "api_calls": 0}

        # Group by batch key to optimize API calls
        grouped = self._group_requests_by_batch_key(batch)

        for batch_key, requests in grouped.items():
            try:
                # Extract assets from requests
                assets = [r.asset for r in requests]
                data_type = requests[0].data_type
                provider_name = requests[0].provider

                # Get provider
                provider = self.provider_registry.get_provider(provider_name)
                if not provider:
                    logger.error(f"Provider not found: {provider_name}")
                    stats["failed"] += len(requests)
                    continue

                # Batch fetch data from provider
                if data_type == DataType.PRICE:
                    # Check if provider supports batch operations
                    if hasattr(provider, "get_prices_batch"):
                        # Single API call for all assets
                        prices = await provider.get_prices_batch(assets)
                        stats["api_calls"] += 1

                        # Update cache for each asset
                        cache_items = [
                            (asset, provider_name, price)
                            for asset, price in zip(assets, prices, strict=False)
                            if price is not None
                        ]

                        if cache_items:
                            success_count = await self.cache_manager.set_prices_batch(cache_items)
                            stats["success"] += success_count
                            stats["failed"] += (len(requests) - success_count)

                            # Calculate API calls saved
                            stats["api_calls_saved"] = len(requests) - 1

                    else:
                        # Fall back to individual calls
                        for request in requests:
                            try:
                                price = await provider.get_price(request.asset)
                                stats["api_calls"] += 1

                                if price:
                                    await self.cache_manager.set_price(
                                        request.asset,
                                        provider_name,
                                        price
                                    )
                                    stats["success"] += 1
                                else:
                                    stats["failed"] += 1

                            except Exception as e:
                                logger.error(
                                    f"Failed to update price: {e}",
                                    asset=request.asset.symbol
                                )
                                stats["failed"] += 1

                elif data_type == DataType.FUNDAMENTALS:
                    # Similar pattern for fundamentals
                    for request in requests:
                        try:
                            fundamentals = await provider.get_fundamentals(request.asset)
                            stats["api_calls"] += 1

                            if fundamentals:
                                await self.cache_manager.set_fundamentals(
                                    request.asset,
                                    provider_name,
                                    fundamentals
                                )
                                stats["success"] += 1
                            else:
                                stats["failed"] += 1

                        except Exception as e:
                            logger.error(
                                f"Failed to update fundamentals: {e}",
                                asset=request.asset.symbol
                            )
                            stats["failed"] += 1

            except Exception as e:
                logger.error(f"Batch processing error: {e}", batch_key=batch_key)
                stats["failed"] += len(requests)

        return stats

    async def _run_batch_cycle(self) -> None:
        """Run a single batch processing cycle"""
        # Check if we should process during this hour
        current_hour = datetime.now(UTC).hour
        is_low_load = current_hour in self.low_load_hours

        if not is_low_load and len(self.pending_requests) < self.batch_size * 2:
            # During high-load hours, only process if queue is getting full
            logger.debug("Skipping batch cycle - high load period", hour=current_hour)
            return

        async with self.pending_lock:
            if not self.pending_requests:
                return

            # Get next batch
            batch = self._get_next_batch()

            if not batch:
                return

            # Remove from pending
            for request in batch:
                self.pending_requests.remove(request)

        logger.info(
            "Processing batch",
            size=len(batch),
            remaining=len(self.pending_requests),
            is_low_load=is_low_load
        )

        # Process batch
        stats = await self._process_batch(batch)

        # Update statistics
        self.batches_processed += 1
        self.successful_updates += stats["success"]
        self.failed_updates += stats["failed"]
        self.api_calls_saved += stats.get("api_calls_saved", 0)

        logger.info(
            "Batch complete",
            success=stats["success"],
            failed=stats["failed"],
            api_calls=stats["api_calls"],
            api_calls_saved=stats.get("api_calls_saved", 0)
        )

    async def start(self) -> None:
        """Start the batch scheduler"""
        if self.is_running:
            logger.warning("Batch scheduler already running")
            return

        self.is_running = True

        async def scheduler_loop():
            while self.is_running:
                try:
                    await self._run_batch_cycle()
                except Exception as e:
                    logger.error(f"Scheduler cycle error: {e}")

                # Wait for next cycle
                await asyncio.sleep(self.batch_interval_seconds)

        self._scheduler_task = asyncio.create_task(scheduler_loop())
        logger.info(
            "Batch scheduler started",
            batch_size=self.batch_size,
            interval_seconds=self.batch_interval_seconds,
            low_load_hours=self.low_load_hours
        )

    async def stop(self) -> None:
        """Stop the batch scheduler"""
        self.is_running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task

        logger.info("Batch scheduler stopped")

    async def flush_pending(self) -> Dict[str, int]:
        """
        Process all pending requests immediately

        Returns:
            Stats dict with results
        """
        total_stats = {"success": 0, "failed": 0, "batches": 0}

        while True:
            async with self.pending_lock:
                if not self.pending_requests:
                    break

                batch = self._get_next_batch()
                if not batch:
                    break

                for request in batch:
                    self.pending_requests.remove(request)

            stats = await self._process_batch(batch)
            total_stats["success"] += stats["success"]
            total_stats["failed"] += stats["failed"]
            total_stats["batches"] += 1

        logger.info(
            "Pending requests flushed",
            batches=total_stats["batches"],
            success=total_stats["success"],
            failed=total_stats["failed"]
        )

        return total_stats

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return {
            "is_running": self.is_running,
            "pending_requests": len(self.pending_requests),
            "total_requests": self.total_requests,
            "batches_processed": self.batches_processed,
            "successful_updates": self.successful_updates,
            "failed_updates": self.failed_updates,
            "api_calls_saved": self.api_calls_saved,
            "batch_size": self.batch_size,
            "interval_seconds": self.batch_interval_seconds,
        }

    def clear_pending(self) -> int:
        """Clear all pending requests"""
        count = len(self.pending_requests)
        self.pending_requests.clear()
        logger.info("Pending requests cleared", count=count)
        return count
