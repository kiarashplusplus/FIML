"""
Cache Warming - Predictive Cache Pre-fetching
Analyzes query patterns and pre-warms cache during off-peak hours
"""

import asyncio
import contextlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType

logger = get_logger(__name__)


class QueryPattern:
    """Tracks query patterns for a symbol"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.request_count = 0
        self.last_accessed = datetime.now(UTC)
        self.hourly_distribution: Dict[int, int] = defaultdict(int)  # hour -> count
        self.data_types_requested: Dict[DataType, int] = defaultdict(int)

    def record_access(self, data_type: DataType, hour: int) -> None:
        """Record a cache access"""
        self.request_count += 1
        self.last_accessed = datetime.now(UTC)
        self.hourly_distribution[hour] += 1
        self.data_types_requested[data_type] += 1

    def get_peak_hours(self, top_n: int = 3) -> List[int]:
        """Get the top N peak hours for this symbol"""
        sorted_hours = sorted(self.hourly_distribution.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:top_n]]

    def get_priority_score(self, now: datetime, market_events: Set[str]) -> float:
        """
        Calculate priority score for warming

        Factors:
        - Request frequency (last 7 days)
        - Recency of last access
        - Time of day pattern match
        - Market event relevance
        """
        # Base score from request frequency
        frequency_score = min(self.request_count / 100, 10.0)

        # Recency bonus (decay over 7 days)
        hours_since_access = (now - self.last_accessed).total_seconds() / 3600
        recency_score = max(0, 10 - (hours_since_access / 24))

        # Time pattern bonus
        current_hour = now.hour
        pattern_score = 5.0 if current_hour in self.get_peak_hours() else 0.0

        # Market event bonus
        event_score = 10.0 if self.symbol in market_events else 0.0

        total_score = frequency_score + recency_score + pattern_score + event_score
        return total_score


class PredictiveCacheWarmer:
    """
    Predictive cache warming based on query pattern analysis

    Features:
    - Analyzes query patterns from cache access logs
    - Identifies frequently requested symbols
    - Pre-fetches during off-peak hours
    - Prioritizes based on request frequency, time patterns, and market events
    - Configurable warming schedules
    - Monitors warming effectiveness
    """

    def __init__(
        self,
        cache_manager: Any,
        provider_registry: Any,
        warming_schedule: Optional[List[int]] = None,  # Hours to warm cache
        min_request_threshold: int = 10,  # Minimum requests to qualify for warming
        max_symbols_per_batch: int = 50,
    ):
        """
        Initialize cache warmer

        Args:
            cache_manager: Cache manager instance
            provider_registry: Provider registry for data fetching
            warming_schedule: List of hours (0-23) to run warming
            min_request_threshold: Minimum requests to qualify for warming
            max_symbols_per_batch: Maximum symbols to warm per batch
        """
        self.cache_manager = cache_manager
        self.provider_registry = provider_registry
        self.warming_schedule = warming_schedule or [0, 6, 12, 18]  # Every 6 hours
        self.min_request_threshold = min_request_threshold
        self.max_symbols_per_batch = max_symbols_per_batch

        # Pattern tracking
        self.query_patterns: Dict[str, QueryPattern] = {}

        # Market events (earnings dates, etc.)
        self.market_events: Set[str] = set()

        # Warming statistics
        self.total_warmed = 0
        self.successful_warms = 0
        self.failed_warms = 0
        self.warming_hits = 0  # Requests served from warmed cache

        # Running state
        self.is_running = False
        self._warming_task: Optional[asyncio.Task] = None

    def record_cache_access(
        self, symbol: str, data_type: DataType, timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a cache access for pattern analysis

        Args:
            symbol: Asset symbol accessed
            data_type: Type of data requested
            timestamp: Access timestamp (default: now)
        """
        if symbol not in self.query_patterns:
            self.query_patterns[symbol] = QueryPattern(symbol)

        timestamp = timestamp or datetime.now(UTC)
        hour = timestamp.hour

        self.query_patterns[symbol].record_access(data_type, hour)

        logger.debug("Cache access recorded", symbol=symbol, data_type=data_type.value, hour=hour)

    def add_market_event(self, symbol: str, event_type: str = "earnings") -> None:
        """
        Add a market event for a symbol (e.g., earnings date)

        Args:
            symbol: Asset symbol
            event_type: Type of event
        """
        self.market_events.add(symbol)
        logger.info("Market event added", symbol=symbol, event_type=event_type)

    def get_symbols_to_warm(
        self, now: Optional[datetime] = None, limit: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """
        Get prioritized list of symbols to warm

        Args:
            now: Current timestamp (default: utcnow)
            limit: Maximum symbols to return

        Returns:
            List of (symbol, priority_score) tuples, sorted by priority
        """
        now = now or datetime.now(UTC)
        limit = limit or self.max_symbols_per_batch

        # Filter symbols meeting threshold
        candidates = {
            symbol: pattern
            for symbol, pattern in self.query_patterns.items()
            if pattern.request_count >= self.min_request_threshold
        }

        # Calculate priority scores
        scored_symbols = [
            (symbol, pattern.get_priority_score(now, self.market_events))
            for symbol, pattern in candidates.items()
        ]

        # Sort by priority (descending)
        scored_symbols.sort(key=lambda x: x[1], reverse=True)

        # Return top symbols
        return scored_symbols[:limit]

    async def warm_symbol(self, symbol: str, data_types: Optional[List[DataType]] = None) -> bool:
        """
        Warm cache for a specific symbol

        Args:
            symbol: Asset symbol to warm
            data_types: Data types to pre-fetch (default: price, fundamentals)

        Returns:
            True if successful
        """
        data_types = data_types or [DataType.PRICE, DataType.FUNDAMENTALS]
        asset = Asset(symbol=symbol, asset_type=AssetType.EQUITY)

        success = True

        for data_type in data_types:
            try:
                # Fetch fresh data from provider
                if data_type == DataType.PRICE:
                    # Get price from primary provider
                    provider = self.provider_registry.get_provider_for_data_type(data_type, asset)
                    if provider:
                        price_data = await provider.get_price(asset)
                        if price_data:
                            await self.cache_manager.set_price(asset, provider.name, price_data)
                            logger.debug("Warmed price cache", symbol=symbol)
                        else:
                            success = False

                elif data_type == DataType.FUNDAMENTALS:
                    provider = self.provider_registry.get_provider_for_data_type(data_type, asset)
                    if provider:
                        fundamentals = await provider.get_fundamentals(asset)
                        if fundamentals:
                            await self.cache_manager.set_fundamentals(
                                asset, provider.name, fundamentals
                            )
                            logger.debug("Warmed fundamentals cache", symbol=symbol)
                        else:
                            success = False

            except Exception as e:
                logger.error(f"Failed to warm cache for {symbol}: {e}", data_type=data_type.value)
                success = False

        if success:
            self.successful_warms += 1
        else:
            self.failed_warms += 1

        self.total_warmed += 1

        return success

    async def warm_cache_batch(self, symbols: List[str], concurrency: int = 10) -> Dict[str, bool]:
        """
        Warm cache for multiple symbols concurrently

        Args:
            symbols: List of symbols to warm
            concurrency: Maximum concurrent warming operations

        Returns:
            Dict mapping symbol to success status
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def warm_with_limit(symbol: str) -> Tuple[str, bool]:
            async with semaphore:
                success = await self.warm_symbol(symbol)
                return symbol, success

        tasks = [warm_with_limit(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        result_dict = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Warming task failed: {result}")
            else:
                # symbol, success = result  # This assumes result is a tuple, but it could be an exception
                if isinstance(result, tuple) and len(result) == 2:
                    symbol, success = result
                    result_dict[symbol] = success

        logger.info(
            "Cache warming batch complete",
            total=len(symbols),
            successful=sum(result_dict.values()),
            failed=len(symbols) - sum(result_dict.values()),
        )

        return result_dict

    async def run_warming_cycle(self) -> None:
        """Run a single warming cycle"""
        now = datetime.now(UTC)

        # Check if we should run warming at this hour
        if now.hour not in self.warming_schedule:
            logger.debug("Skipping warming cycle - not in schedule", hour=now.hour)
            return

        logger.info("Starting cache warming cycle", hour=now.hour)

        # Get symbols to warm
        symbols_to_warm = self.get_symbols_to_warm(now)

        if not symbols_to_warm:
            logger.info("No symbols to warm")
            return

        # Extract just the symbols
        symbols = [symbol for symbol, _ in symbols_to_warm]

        # Log top symbols
        logger.info("Top symbols for warming", symbols=symbols[:10], total=len(symbols))

        # Warm cache
        await self.warm_cache_batch(symbols)

        logger.info(
            "Cache warming cycle complete",
            total_warmed=self.total_warmed,
            successful=self.successful_warms,
            failed=self.failed_warms,
        )

    async def start_background_warming(self, interval_minutes: int = 60) -> None:
        """
        Start background cache warming

        Args:
            interval_minutes: How often to check for warming (default: 60 minutes)
        """
        if self.is_running:
            logger.warning("Background warming already running")
            return

        self.is_running = True

        async def warming_loop() -> None:
            while self.is_running:
                try:
                    await self.run_warming_cycle()
                except Exception as e:
                    logger.error(f"Warming cycle error: {e}")

                # Sleep until next cycle
                await asyncio.sleep(interval_minutes * 60)

        self._warming_task = asyncio.create_task(warming_loop())
        logger.info("Background cache warming started", interval_minutes=interval_minutes)

    async def stop_background_warming(self) -> None:
        """Stop background cache warming"""
        self.is_running = False

        if self._warming_task:
            self._warming_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._warming_task

        logger.info("Background cache warming stopped")

    def get_warming_stats(self) -> Dict[str, Any]:
        """Get warming statistics"""
        success_rate = (
            (self.successful_warms / self.total_warmed * 100) if self.total_warmed > 0 else 0.0
        )

        return {
            "total_warmed": self.total_warmed,
            "successful": self.successful_warms,
            "failed": self.failed_warms,
            "success_rate_percent": round(success_rate, 2),
            "warming_hits": self.warming_hits,
            "tracked_symbols": len(self.query_patterns),
            "market_events": len(self.market_events),
            "is_running": self.is_running,
        }

    def clear_old_patterns(self, days: int = 7) -> int:
        """
        Clear query patterns older than specified days

        Args:
            days: Number of days to retain

        Returns:
            Number of patterns removed
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        old_patterns = [
            symbol
            for symbol, pattern in self.query_patterns.items()
            if pattern.last_accessed < cutoff
        ]

        for symbol in old_patterns:
            del self.query_patterns[symbol]

        logger.info("Cleared old query patterns", removed=len(old_patterns))
        return len(old_patterns)
