"""
Cache Manager - Coordinates L1 and L2 caches
"""

import time
from datetime import UTC, datetime
from datetime import time as time_obj
from typing import Any, Callable, Dict, List, Optional, Tuple

from fiml.cache.analytics import cache_analytics
from fiml.cache.l1_cache import l1_cache
from fiml.cache.l2_cache import l2_cache
from fiml.cache.utils import calculate_percentile
from fiml.core.config import settings
from fiml.core.logging import get_logger
from fiml.core.models import Asset, DataType

logger = get_logger(__name__)


class CacheManager:
    """
    Coordinates L1 (Redis) and L2 (PostgreSQL) caches

    Strategy:
    1. Check L1 first (10-100ms)
    2. If miss, check L2 (300-700ms)
    3. If hit in L2, populate L1
    4. If miss in both, return None
    5. On write, update both L1 and L2

    Features:
    - Latency tracking for L1 and L2 operations
    - Hit rate measurement
    - Eviction statistics
    - Dynamic TTL based on data volatility and market hours
    - Read-through cache pattern
    - Integrated analytics
    """

    def __init__(self) -> None:
        self.l1 = l1_cache
        self.l2 = l2_cache
        self._initialized = False

        # Metrics tracking
        self._l1_hits = 0
        self._l1_misses = 0
        self._l2_hits = 0
        self._l2_misses = 0
        self._l1_latencies: List[float] = []
        self._l2_latencies: List[float] = []

        # Analytics integration
        self.analytics = cache_analytics

        # Market hours configuration (NYSE default: 9:30 AM - 4:00 PM ET)
        self.market_open = time_obj(9, 30)
        self.market_close = time_obj(16, 0)

    async def initialize(self) -> None:
        """Initialize both cache layers"""
        await self.l1.initialize()
        await self.l2.initialize()
        self._initialized = True
        logger.info("Cache manager initialized")

    async def shutdown(self) -> None:
        """Shutdown both cache layers"""
        await self.l1.shutdown()
        await self.l2.shutdown()
        self._initialized = False
        logger.info("Cache manager shutdown")

    async def get_price(
        self, asset: Asset, provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get price with L1 -> L2 fallback

        Args:
            asset: Asset to query
            provider: Specific provider (optional)

        Returns:
            Price data or None
        """
        # Build cache key
        l1_key = self.l1.build_key("price", asset.symbol, provider or "any")

        # Try L1 first
        l1_result = await self.l1.get(l1_key)
        if l1_result:
            logger.debug("Price from L1 cache", asset=asset.symbol)
            return dict(l1_result) if isinstance(l1_result, dict) else l1_result

        # Try L2
        # Note: Would need asset_id lookup first in production
        logger.debug("Price L1 miss, trying L2", asset=asset.symbol)
        # l2_result = await self.l2.get_price(asset_id, provider)
        # if l2_result:
        #     # Populate L1
        #     await self.l1.set(l1_key, l2_result, self._get_ttl(DataType.PRICE))
        #     return l2_result

        return None

    async def set_price(
        self,
        asset: Asset,
        provider: str,
        price_data: Dict[str, Any],
    ) -> bool:
        """
        Set price in both caches with dynamic TTL

        Args:
            asset: Asset
            provider: Provider name
            price_data: Price data dictionary

        Returns:
            True if successful
        """
        l1_key = self.l1.build_key("price", asset.symbol, provider)
        ttl = self._get_ttl(DataType.PRICE, asset)

        # Set in L1
        l1_success = await self.l1.set(l1_key, price_data, ttl)

        # Set in L2 (async, don't wait)
        # In production, would insert into PostgreSQL
        # l2_success = await self.l2.set_price(asset_id, provider, ...)

        logger.debug(
            "Price cached",
            asset=asset.symbol,
            provider=provider,
            l1=l1_success,
            ttl=ttl
        )
        return bool(l1_success)

    async def get_fundamentals(
        self, asset: Asset, provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get fundamentals with L1 -> L2 fallback"""
        l1_key = self.l1.build_key("fundamentals", asset.symbol, provider or "any")

        # Try L1
        l1_result = await self.l1.get(l1_key)
        if l1_result:
            logger.debug("Fundamentals from L1 cache", asset=asset.symbol)
            return dict(l1_result) if isinstance(l1_result, dict) else l1_result

        # Try L2
        logger.debug("Fundamentals L1 miss, trying L2", asset=asset.symbol)
        # In production: l2_result = await self.l2.get_fundamentals(asset_id, provider)

        return None

    async def set_fundamentals(
        self,
        asset: Asset,
        provider: str,
        data: Dict[str, Any],
    ) -> bool:
        """Set fundamentals in both caches with dynamic TTL"""
        l1_key = self.l1.build_key("fundamentals", asset.symbol, provider)
        ttl = self._get_ttl(DataType.FUNDAMENTALS, asset)

        # Set in L1
        l1_success = await self.l1.set(l1_key, data, ttl)

        # Set in L2
        # In production: await self.l2.set_fundamentals(asset_id, provider, data, ttl)

        logger.debug(
            "Fundamentals cached",
            asset=asset.symbol,
            provider=provider,
            ttl=ttl
        )
        return bool(l1_success)

    async def invalidate_asset(self, asset: Asset) -> int:
        """Invalidate all cached data for an asset"""
        pattern = f"*:{asset.symbol}:*"
        deleted = await self.l1.clear_pattern(pattern)
        logger.info("Invalidated cache for asset", asset=asset.symbol, deleted=deleted)
        return int(deleted) if deleted else 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get combined cache statistics with performance metrics

        Returns:
            Comprehensive statistics including hit rates and latencies
        """
        l1_stats = await self.l1.get_stats()

        # Calculate hit rates
        total_l1_ops = self._l1_hits + self._l1_misses
        l1_hit_rate = (self._l1_hits / total_l1_ops * 100) if total_l1_ops > 0 else 0.0

        total_l2_ops = self._l2_hits + self._l2_misses
        l2_hit_rate = (self._l2_hits / total_l2_ops * 100) if total_l2_ops > 0 else 0.0

        # Calculate average latencies
        avg_l1_latency = sum(self._l1_latencies) / len(self._l1_latencies) if self._l1_latencies else 0.0
        avg_l2_latency = sum(self._l2_latencies) / len(self._l2_latencies) if self._l2_latencies else 0.0

        # Calculate percentiles for L1 latency
        l1_p50 = calculate_percentile(self._l1_latencies, 50)
        l1_p95 = calculate_percentile(self._l1_latencies, 95)
        l1_p99 = calculate_percentile(self._l1_latencies, 99)

        return {
            "l1": {
                **l1_stats,
                "hits": self._l1_hits,
                "misses": self._l1_misses,
                "hit_rate_percent": round(l1_hit_rate, 2),
                "avg_latency_ms": round(avg_l1_latency, 2),
                "p50_latency_ms": round(l1_p50, 2),
                "p95_latency_ms": round(l1_p95, 2),
                "p99_latency_ms": round(l1_p99, 2),
            },
            "l2": {
                "status": "initialized" if self.l2._initialized else "not_initialized",
                "hits": self._l2_hits,
                "misses": self._l2_misses,
                "hit_rate_percent": round(l2_hit_rate, 2),
                "avg_latency_ms": round(avg_l2_latency, 2),
            },
            "overall": {
                "total_requests": total_l1_ops,
                "l1_hit_rate": round(l1_hit_rate, 2),
                "l2_hit_rate": round(l2_hit_rate, 2),
            }
        }

    def _track_l1_latency(self, latency_ms: float) -> None:
        """Track L1 latency (keep last 1000 measurements)"""
        self._l1_latencies.append(latency_ms)
        if len(self._l1_latencies) > 1000:
            self._l1_latencies.pop(0)

    def _track_l2_latency(self, latency_ms: float) -> None:
        """Track L2 latency (keep last 1000 measurements)"""
        self._l2_latencies.append(latency_ms)
        if len(self._l2_latencies) > 1000:
            self._l2_latencies.pop(0)

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """
        Calculate percentile value from a list of numbers

        Args:
            values: List of numeric values
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        return calculate_percentile(values, percentile)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with latency tracking

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Try L1 first
        start = time.perf_counter()
        value = await self.l1.get(key)
        l1_latency_ms = (time.perf_counter() - start) * 1000
        self._track_l1_latency(l1_latency_ms)

        if value is not None:
            self._l1_hits += 1
            return value

        self._l1_misses += 1
        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """
        Set value in cache with latency tracking

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live

        Returns:
            True if successful
        """
        start = time.perf_counter()
        success = await self.l1.set(key, value, ttl_seconds)
        l1_latency_ms = (time.perf_counter() - start) * 1000
        self._track_l1_latency(l1_latency_ms)

        return bool(success)

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        result = await self.l1.delete(key)
        return bool(result)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        result = await self.l1.exists(key)
        return bool(result)

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        result = await self.l1.clear_pattern(pattern)
        return int(result) if result else 0

    def _get_ttl(self, data_type: DataType, asset: Optional[Asset] = None) -> int:
        """
        Get intelligent TTL for data type with dynamic adjustments

        Factors:
        - Data type volatility
        - Market hours (shorter TTL during trading)
        - Asset type (crypto vs stocks)
        - Weekend/holiday extended TTL
        """
        # Base TTL from settings
        ttl_map = {
            DataType.PRICE: settings.cache_ttl_price,
            DataType.FUNDAMENTALS: settings.cache_ttl_fundamentals,
            DataType.TECHNICAL: settings.cache_ttl_technical,
            DataType.NEWS: settings.cache_ttl_news,
            DataType.MACRO: settings.cache_ttl_macro,
        }
        base_ttl = ttl_map.get(data_type, 300)

        # Check if market is currently open
        now = datetime.now(UTC)
        current_time = now.time()
        is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6

        # Dynamic adjustments for price data
        if data_type == DataType.PRICE:
            # Crypto trades 24/7 - shorter TTL always
            if asset and asset.asset_type == "crypto":
                return min(base_ttl, 60)  # Max 1 minute for crypto

            # Stock market hours
            if is_weekday and self.market_open <= current_time <= self.market_close:
                # During market hours - use base TTL (shorter)
                return base_ttl
            else:
                # After hours or weekends - extend TTL by 4x
                return base_ttl * 4

        # Fundamentals have longer TTL on weekends
        elif data_type == DataType.FUNDAMENTALS:
            if not is_weekday:
                return base_ttl * 2  # Double TTL on weekends

        # News can be extended on weekends
        elif data_type == DataType.NEWS:
            if not is_weekday:
                return int(base_ttl * 1.5)

        return base_ttl

    async def get_with_read_through(
        self,
        key: str,
        data_type: DataType,
        fetch_fn: Callable[[], Any],
        asset: Optional[Asset] = None
    ) -> Optional[Any]:
        """
        Read-through cache pattern: fetch from source if not in cache

        Args:
            key: Cache key
            data_type: Type of data
            fetch_fn: Async function to fetch data if cache miss
            asset: Asset (for TTL calculation)

        Returns:
            Cached or fetched data
        """
        # Try cache first
        start = time.perf_counter()
        value = await self.l1.get(key)
        l1_latency_ms = (time.perf_counter() - start) * 1000

        if value is not None:
            self._l1_hits += 1
            self._track_l1_latency(l1_latency_ms)

            # Record analytics
            self.analytics.record_cache_access(
                data_type=data_type,
                is_hit=True,
                latency_ms=l1_latency_ms,
                cache_level="l1",
                key=key
            )

            return value

        self._l1_misses += 1

        # Record analytics for miss
        self.analytics.record_cache_access(
            data_type=data_type,
            is_hit=False,
            latency_ms=l1_latency_ms,
            cache_level="l1",
            key=key
        )

        # Fetch from source
        try:
            fetched_value = await fetch_fn()

            if fetched_value is not None:
                # Store in cache with dynamic TTL
                ttl = self._get_ttl(data_type, asset)
                await self.l1.set(key, fetched_value, ttl)

                logger.debug(
                    "Read-through cache populated",
                    key=key,
                    data_type=data_type.value,
                    ttl=ttl
                )

            return fetched_value

        except Exception as e:
            logger.error(f"Read-through fetch error: {e}", key=key)
            self.analytics.record_error(data_type)
            return None

    async def get_prices_batch(
        self, assets: List[Asset], provider: Optional[str] = None
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Get multiple prices with L1 cache batch optimization

        Args:
            assets: List of assets to query
            provider: Specific provider (optional)

        Returns:
            List of price data (None for misses)
        """
        # Build cache keys for all assets
        l1_keys = [self.l1.build_key("price", asset.symbol, provider or "any") for asset in assets]

        # Try L1 batch get with latency tracking
        start = time.perf_counter()
        results = await self.l1.get_many(l1_keys)
        l1_latency_ms = (time.perf_counter() - start) * 1000
        self._track_l1_latency(l1_latency_ms)

        hits = sum(1 for r in results if r is not None)
        self._l1_hits += hits
        self._l1_misses += (len(results) - hits)

        logger.debug("Batch price lookup", total=len(assets), l1_hits=hits, latency_ms=f"{l1_latency_ms:.2f}")

        # Ensure proper typing for return value
        typed_results: List[Optional[Dict[str, Any]]] = [dict(r) if isinstance(r, dict) else r for r in results]
        return typed_results

    async def set_prices_batch(
        self,
        items: List[tuple[Asset, str, Dict[str, Any]]],
    ) -> int:
        """
        Set multiple prices in L1 cache using batch optimization with dynamic TTL

        Args:
            items: List of (asset, provider, price_data) tuples

        Returns:
            Number of successfully cached items
        """
        # Build cache items with dynamic TTL per asset
        cache_items: List[Tuple[str, Any, Optional[int]]] = []

        for asset, provider, price_data in items:
            ttl = self._get_ttl(DataType.PRICE, asset)
            key = self.l1.build_key("price", asset.symbol, provider)
            cache_items.append((key, price_data, ttl))

        # Batch set in L1
        success_count = await self.l1.set_many(cache_items)

        logger.debug("Batch price set", total=len(items), success=success_count)
        return int(success_count) if success_count else 0


# Global cache manager instance
cache_manager = CacheManager()
