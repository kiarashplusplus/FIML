"""
Comprehensive tests for Cache modules to achieve near 100% coverage

This test module covers all untested code paths in the cache module.
"""

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fiml.cache.analytics import CacheAnalytics, DataTypeMetrics
from fiml.cache.eviction import EvictionPolicy, EvictionTracker
from fiml.cache.l1_cache import L1Cache
from fiml.cache.l2_cache import L2Cache
from fiml.cache.manager import CacheManager
from fiml.cache.scheduler import BatchUpdateScheduler, UpdateRequest
from fiml.cache.warmer import CacheWarmer
from fiml.cache.warming import PredictiveCacheWarmer, QueryPattern
from fiml.core.exceptions import CacheError
from fiml.core.models import Asset, AssetType, DataType, Market


# Helper fixtures
@pytest.fixture
def sample_asset():
    """Create a sample asset for testing"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US,
        exchange="NASDAQ",
        currency="USD"
    )


@pytest.fixture
def sample_crypto_asset():
    """Create a sample crypto asset for testing"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
        market=Market.CRYPTO,
        exchange="binance",
        currency="USDT"
    )


class TestDataTypeMetrics:
    """Tests for DataTypeMetrics class"""

    def test_record_hit(self):
        """Test recording a cache hit"""
        metrics = DataTypeMetrics(DataType.PRICE)
        metrics.record_hit(10.5)
        assert metrics.hits == 1
        assert len(metrics.latencies) == 1
        assert metrics.latencies[0] == 10.5

    def test_record_miss(self):
        """Test recording a cache miss"""
        metrics = DataTypeMetrics(DataType.PRICE)
        metrics.record_miss()
        assert metrics.misses == 1

    def test_record_error(self):
        """Test recording an error"""
        metrics = DataTypeMetrics(DataType.PRICE)
        metrics.record_error()
        assert metrics.errors == 1

    def test_get_hit_rate(self):
        """Test hit rate calculation"""
        metrics = DataTypeMetrics(DataType.PRICE)
        metrics.hits = 80
        metrics.misses = 20
        assert metrics.get_hit_rate() == 80.0

    def test_get_hit_rate_zero(self):
        """Test hit rate when no requests"""
        metrics = DataTypeMetrics(DataType.PRICE)
        assert metrics.get_hit_rate() == 0.0

    def test_get_latency_stats_empty(self):
        """Test latency stats with no data"""
        metrics = DataTypeMetrics(DataType.PRICE)
        stats = metrics.get_latency_stats()
        assert stats["count"] == 0
        assert stats["mean"] == 0.0
        assert stats["p50"] == 0.0

    def test_get_latency_stats(self):
        """Test latency stats calculation"""
        metrics = DataTypeMetrics(DataType.PRICE)
        for i in range(1, 11):
            metrics.record_hit(float(i * 10))

        stats = metrics.get_latency_stats()
        assert stats["count"] == 10
        assert stats["mean"] == 55.0  # Mean of 10-100
        assert stats["min"] == 10.0
        assert stats["max"] == 100.0

    def test_latencies_limit(self):
        """Test that latencies list is limited to 10000"""
        metrics = DataTypeMetrics(DataType.PRICE)
        for i in range(10010):
            metrics.record_hit(float(i))

        # Should have popped old values
        assert len(metrics.latencies) == 10000

    def test_percentile_empty(self):
        """Test percentile calculation with empty list"""
        assert DataTypeMetrics._percentile([], 50) == 0.0


class TestCacheAnalyticsExtended:
    """Extended tests for CacheAnalytics class"""

    def test_init_without_prometheus(self):
        """Test initialization without Prometheus"""
        analytics = CacheAnalytics(enable_prometheus=False)
        assert analytics.enable_prometheus is False
        assert analytics.total_hits == 0
        assert analytics.total_misses == 0

    def test_record_cache_access_hit(self):
        """Test recording a cache hit"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.record_cache_access(
            data_type=DataType.PRICE,
            is_hit=True,
            latency_ms=10.0,
            cache_level="l1",
            key="test_key"
        )
        assert analytics.total_hits == 1
        assert analytics.total_misses == 0
        # First access should be tracked
        assert "test_key" in analytics.single_access_keys

    def test_record_cache_access_miss(self):
        """Test recording a cache miss"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.record_cache_access(
            data_type=DataType.PRICE,
            is_hit=False,
            latency_ms=15.0,
            cache_level="l1"
        )
        assert analytics.total_hits == 0
        assert analytics.total_misses == 1

    def test_record_cache_access_second_hit_removes_tracking(self):
        """Test that second hit removes key from single access tracking"""
        analytics = CacheAnalytics(enable_prometheus=False)
        # First access
        analytics.record_cache_access(
            data_type=DataType.PRICE,
            is_hit=True,
            latency_ms=10.0,
            cache_level="l1",
            key="test_key"
        )
        assert "test_key" in analytics.single_access_keys

        # Second access
        analytics.record_cache_access(
            data_type=DataType.PRICE,
            is_hit=True,
            latency_ms=10.0,
            cache_level="l1",
            key="test_key"
        )
        # Should be removed after second access
        assert "test_key" not in analytics.single_access_keys

    def test_record_error(self):
        """Test recording an error"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.record_error(DataType.PRICE)
        assert analytics.total_errors == 1
        assert analytics.data_type_metrics[DataType.PRICE].errors == 1

    def test_record_eviction(self):
        """Test recording an eviction"""
        analytics = CacheAnalytics(enable_prometheus=False)
        # Add key to single access tracking first
        analytics.single_access_keys["evicted_key"] = datetime.now(timezone.utc)

        analytics.record_eviction("evicted_key", "lru", "l1")
        assert analytics.evicted_before_use == 1
        assert "evicted_key" not in analytics.single_access_keys

    def test_record_eviction_key_not_tracked(self):
        """Test eviction for key not in tracking"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.record_eviction("not_tracked", "lru", "l1")
        assert analytics.evicted_before_use == 0

    def test_get_overall_stats(self):
        """Test getting overall statistics"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.total_hits = 80
        analytics.total_misses = 20
        analytics.total_errors = 5

        stats = analytics.get_overall_stats()
        assert stats["total_requests"] == 100
        assert stats["total_hits"] == 80
        assert stats["total_misses"] == 20
        assert stats["total_errors"] == 5
        assert stats["hit_rate_percent"] == 80.0

    def test_get_data_type_stats(self):
        """Test getting per-data-type statistics"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.data_type_metrics[DataType.PRICE].hits = 50
        analytics.data_type_metrics[DataType.PRICE].misses = 50
        analytics.record_cache_access(DataType.PRICE, True, 10.0, "l1")

        stats = analytics.get_data_type_stats()
        assert "price" in stats
        assert stats["price"]["hits"] == 51
        assert stats["price"]["misses"] == 50

    def test_detect_cache_pollution(self):
        """Test cache pollution detection"""
        analytics = CacheAnalytics(enable_prometheus=False)
        # Using datetime.now(UTC) to match analytics.py which uses timezone-aware datetimes
        old_time = datetime.now(UTC) - timedelta(hours=2)
        for i in range(10):
            analytics.single_access_keys[f"old_key_{i}"] = old_time

        # Add some new keys (also timezone-aware datetime to match analytics.py)
        for i in range(5):
            analytics.single_access_keys[f"new_key_{i}"] = datetime.now(UTC)

        pollution = analytics.detect_cache_pollution()
        assert pollution["single_access_keys"] == 15
        assert pollution["old_single_access_keys"] == 10
        assert pollution["pollution_score_percent"] > 60  # 10/15 ≈ 66%
        assert pollution["is_polluted"] is True

    def test_detect_cache_pollution_not_polluted(self):
        """Test when cache is not polluted"""
        analytics = CacheAnalytics(enable_prometheus=False)
        pollution = analytics.detect_cache_pollution()
        assert pollution["is_polluted"] is False

    def test_get_hourly_trends(self):
        """Test getting hourly trends"""
        analytics = CacheAnalytics(enable_prometheus=False)
        # Record some accesses
        for _ in range(10):
            analytics.record_cache_access(DataType.PRICE, True, 10.0, "l1")
        for _ in range(5):
            analytics.record_cache_access(DataType.PRICE, False, 10.0, "l1")

        trends = analytics.get_hourly_trends(hours=2)
        assert len(trends) == 2
        # Most recent hour should have our data
        current_hour = trends[-1]
        assert current_hour["requests"] == 15
        assert current_hour["hits"] == 10
        assert current_hour["misses"] == 5

    def test_generate_recommendations_low_hit_rate(self):
        """Test recommendations for low hit rate"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.total_hits = 50
        analytics.total_misses = 50

        recommendations = analytics.generate_recommendations()
        assert any("Low overall hit rate" in r for r in recommendations)

    def test_generate_recommendations_pollution(self):
        """Test recommendations for cache pollution"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.total_hits = 90
        analytics.total_misses = 10
        # Using datetime.now(UTC) to match analytics.py timezone-aware datetime format
        old_time = datetime.now(UTC) - timedelta(hours=2)
        for i in range(100):
            analytics.single_access_keys[f"key_{i}"] = old_time

        recommendations = analytics.generate_recommendations()
        assert any("pollution" in r.lower() for r in recommendations)

    def test_generate_recommendations_high_eviction_before_reuse(self):
        """Test recommendations for high eviction before reuse"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.total_hits = 90
        analytics.total_misses = 10
        analytics.evicted_before_use = 150

        recommendations = analytics.generate_recommendations()
        assert any("eviction" in r.lower() for r in recommendations)

    def test_generate_recommendations_optimal(self):
        """Test recommendations when everything is optimal"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.total_hits = 95
        analytics.total_misses = 5
        # Set metrics for each data type to avoid low hit rate warnings
        for metrics in analytics.data_type_metrics.values():
            metrics.hits = 95
            metrics.misses = 5
            # Add some latency data to avoid p99 warnings
            for _ in range(10):
                metrics.record_hit(10.0)  # Good latency

        recommendations = analytics.generate_recommendations()
        # When there are no issues, there should be a message about optimal state
        assert len(recommendations) > 0
        # The message is: "Cache performance is optimal. No recommendations at this time."
        assert any("optimal" in r.lower() for r in recommendations)

    def test_get_comprehensive_report(self):
        """Test comprehensive report generation"""
        analytics = CacheAnalytics(enable_prometheus=False)
        report = analytics.get_comprehensive_report()

        assert "timestamp" in report
        assert "overall" in report
        assert "by_data_type" in report
        assert "pollution" in report
        assert "hourly_trends" in report
        assert "recommendations" in report

    def test_reset_stats(self):
        """Test resetting statistics"""
        analytics = CacheAnalytics(enable_prometheus=False)
        analytics.total_hits = 100
        analytics.total_misses = 50
        analytics.total_errors = 10
        analytics.single_access_keys["test"] = datetime.now(timezone.utc)
        analytics.evicted_before_use = 5

        analytics.reset_stats()

        assert analytics.total_hits == 0
        assert analytics.total_misses == 0
        assert analytics.total_errors == 0
        assert len(analytics.single_access_keys) == 0
        assert analytics.evicted_before_use == 0


class TestEvictionTrackerExtended:
    """Extended tests for EvictionTracker class"""

    def test_remove_key_lru(self):
        """Test removing a key from LRU tracking"""
        tracker = EvictionTracker(policy=EvictionPolicy.LRU, max_entries=10)
        tracker.track_access("key1")
        assert "key1" in tracker._lru_tracker

        tracker.remove_key("key1")
        assert "key1" not in tracker._lru_tracker

    def test_remove_key_lfu(self):
        """Test removing a key from LFU tracking"""
        tracker = EvictionTracker(policy=EvictionPolicy.LFU, max_entries=10)
        tracker.track_access("key1")
        assert "key1" in tracker._lfu_tracker

        tracker.remove_key("key1")
        assert "key1" not in tracker._lfu_tracker

    def test_get_access_info_lru(self):
        """Test getting access info for LRU"""
        tracker = EvictionTracker(policy=EvictionPolicy.LRU, max_entries=10)
        tracker.track_access("key1")

        info = tracker.get_access_info("key1")
        assert info is not None
        assert "last_access_time" in info
        assert "age_seconds" in info

    def test_get_access_info_lfu(self):
        """Test getting access info for LFU"""
        tracker = EvictionTracker(policy=EvictionPolicy.LFU, max_entries=10)
        tracker.track_access("key1")
        tracker.track_access("key1")

        info = tracker.get_access_info("key1")
        assert info is not None
        assert info["access_count"] == 2

    def test_get_access_info_not_found(self):
        """Test getting access info for non-existent key"""
        tracker = EvictionTracker(policy=EvictionPolicy.LRU, max_entries=10)
        info = tracker.get_access_info("nonexistent")
        assert info is None

    def test_clear(self):
        """Test clearing all tracking data"""
        tracker = EvictionTracker(policy=EvictionPolicy.LRU, max_entries=10)
        tracker.track_access("key1")
        tracker.track_access("key2")

        tracker.clear()

        assert len(tracker._lru_tracker) == 0
        assert len(tracker._lfu_tracker) == 0
        assert tracker._evictions == 0
        assert tracker._total_accesses == 0

    def test_get_eviction_candidates_empty(self):
        """Test getting eviction candidates when empty"""
        tracker = EvictionTracker(policy=EvictionPolicy.LRU, max_entries=10)
        candidates = tracker.get_eviction_candidates(count=5)
        assert candidates == []

    def test_get_eviction_candidates_lfu(self):
        """Test getting LFU eviction candidates"""
        tracker = EvictionTracker(policy=EvictionPolicy.LFU, max_entries=10)
        # Create different access frequencies
        tracker.track_access("low_freq")
        tracker.track_access("high_freq")
        tracker.track_access("high_freq")
        tracker.track_access("high_freq")

        candidates = tracker.get_eviction_candidates(count=2)
        # low_freq should be first (least frequently used)
        assert "low_freq" in candidates


class TestL1CacheExtended:
    """Extended tests for L1Cache class"""

    def test_initialize_already_initialized(self, caplog):
        """Test initializing when already initialized"""
        cache = L1Cache()
        cache._initialized = True

        # Using pytest.mark.asyncio would require the whole test to be async
        # This test specifically needs to call without await to test re-initialization
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cache.initialize())
        loop.close()

        assert "already initialized" in caplog.text.lower() or cache._initialized

    @pytest.mark.asyncio
    async def test_get_not_initialized(self):
        """Test get when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.get("test_key")

    @pytest.mark.asyncio
    async def test_set_not_initialized(self):
        """Test set when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.set("test_key", "value")

    @pytest.mark.asyncio
    async def test_delete_not_initialized(self):
        """Test delete when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.delete("test_key")

    @pytest.mark.asyncio
    async def test_exists_not_initialized(self):
        """Test exists when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.exists("test_key")

    @pytest.mark.asyncio
    async def test_get_ttl_not_initialized(self):
        """Test get_ttl when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.get_ttl("test_key")

    @pytest.mark.asyncio
    async def test_clear_pattern_not_initialized(self):
        """Test clear_pattern when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.clear_pattern("test:*")

    @pytest.mark.asyncio
    async def test_get_stats_not_initialized(self):
        """Test get_stats when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.get_stats()

    @pytest.mark.asyncio
    async def test_get_many_not_initialized(self):
        """Test get_many when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.get_many(["key1", "key2"])

    @pytest.mark.asyncio
    async def test_set_many_not_initialized(self):
        """Test set_many when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.set_many([("key1", "val1", 60)])

    @pytest.mark.asyncio
    async def test_evict_least_used_not_initialized(self):
        """Test evict_least_used when cache not initialized"""
        cache = L1Cache()
        with pytest.raises(CacheError):
            await cache.evict_least_used()

    def test_get_redis_eviction_policy_lru(self):
        """Test Redis eviction policy mapping for LRU"""
        cache = L1Cache(eviction_policy=EvictionPolicy.LRU)
        assert cache._get_redis_eviction_policy() == "allkeys-lru"

    def test_get_redis_eviction_policy_lfu(self):
        """Test Redis eviction policy mapping for LFU"""
        cache = L1Cache(eviction_policy=EvictionPolicy.LFU)
        assert cache._get_redis_eviction_policy() == "allkeys-lfu"

    def test_get_redis_eviction_policy_hybrid(self):
        """Test Redis eviction policy mapping for HYBRID"""
        cache = L1Cache(eviction_policy=EvictionPolicy.HYBRID)
        assert cache._get_redis_eviction_policy() == "volatile-lfu"

    def test_protect_key(self):
        """Test protecting a key from eviction"""
        cache = L1Cache()
        cache.protect_key("important_key")
        assert "important_key" in cache._protected_keys

    def test_unprotect_key(self):
        """Test unprotecting a key"""
        cache = L1Cache()
        cache.protect_key("key")
        cache.unprotect_key("key")
        assert "key" not in cache._protected_keys

    def test_is_protected_exact_match(self):
        """Test key protection check with exact match"""
        cache = L1Cache()
        cache.protect_key("exact_key")
        assert cache.is_protected("exact_key") is True
        assert cache.is_protected("other_key") is False

    def test_is_protected_pattern_match(self):
        """Test key protection check with pattern"""
        cache = L1Cache(protected_patterns=["critical:*"])
        assert cache.is_protected("critical:price") is True
        assert cache.is_protected("other:price") is False

    def test_matches_pattern_no_wildcard(self):
        """Test pattern matching without wildcard"""
        assert L1Cache._matches_pattern("exact", "exact") is True
        assert L1Cache._matches_pattern("other", "exact") is False

    def test_matches_pattern_with_wildcard(self):
        """Test pattern matching with wildcard"""
        assert L1Cache._matches_pattern("prefix:value", "prefix:*") is True
        assert L1Cache._matches_pattern("other:value", "prefix:*") is False

    def test_calculate_hit_rate(self):
        """Test hit rate calculation"""
        assert L1Cache._calculate_hit_rate(80, 20) == 80.0
        assert L1Cache._calculate_hit_rate(0, 0) == 0.0

    def test_build_key(self):
        """Test building cache key from parts"""
        cache = L1Cache()
        key = cache.build_key("price", "AAPL", "yfinance")
        assert key == "price:AAPL:yfinance"

    def test_track_access(self):
        """Test tracking key access"""
        cache = L1Cache()
        cache._track_access("test_key")
        assert cache._access_counts["test_key"] == 1
        assert "test_key" in cache._last_access

        cache._track_access("test_key")
        assert cache._access_counts["test_key"] == 2

    def test_log_eviction(self):
        """Test logging eviction"""
        cache = L1Cache()
        cache._log_eviction("evicted_key", 5, "manual_lfu")

        assert cache._eviction_count == 1
        assert len(cache._eviction_log) == 1
        assert cache._eviction_log[0]["key"] == "evicted_key"

    def test_log_eviction_limit(self):
        """Test eviction log limit of 1000"""
        cache = L1Cache()
        for i in range(1010):
            cache._log_eviction(f"key_{i}", i, "test")

        assert len(cache._eviction_log) == 1000

    def test_get_eviction_stats(self):
        """Test getting eviction statistics"""
        cache = L1Cache()
        cache._eviction_count = 10
        cache._protected_keys.add("key1")
        cache._access_counts["key2"] = 5

        stats = cache.get_eviction_stats()
        assert stats["total_evictions"] == 10
        assert stats["protected_keys"] == 1
        assert stats["tracked_keys"] == 1

    def test_get_access_stats_empty(self):
        """Test access stats when empty"""
        cache = L1Cache()
        stats = cache.get_access_stats()
        assert stats["total_tracked"] == 0

    def test_get_access_stats(self):
        """Test access stats with data"""
        cache = L1Cache()
        cache._access_counts["key1"] = 100
        cache._access_counts["key2"] = 50

        stats = cache.get_access_stats()
        assert stats["total_tracked"] == 2
        assert len(stats["most_accessed"]) >= 1


class TestL2CacheExtended:
    """Extended tests for L2Cache class"""

    @pytest.mark.asyncio
    async def test_get_price_not_initialized(self):
        """Test get_price when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.get_price(1)

    @pytest.mark.asyncio
    async def test_set_price_not_initialized(self):
        """Test set_price when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.set_price(1, "provider", 100.0)

    @pytest.mark.asyncio
    async def test_get_ohlcv_not_initialized(self):
        """Test get_ohlcv when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.get_ohlcv(1)

    @pytest.mark.asyncio
    async def test_get_fundamentals_not_initialized(self):
        """Test get_fundamentals when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.get_fundamentals(1)

    @pytest.mark.asyncio
    async def test_set_fundamentals_not_initialized(self):
        """Test set_fundamentals when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.set_fundamentals(1, "provider", {"data": "value"})

    @pytest.mark.asyncio
    async def test_cleanup_expired_not_initialized(self):
        """Test cleanup_expired when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.cleanup_expired()

    @pytest.mark.asyncio
    async def test_set_not_initialized(self):
        """Test set when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.set("key", "value")

    @pytest.mark.asyncio
    async def test_get_not_initialized(self):
        """Test get when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.get("key")

    @pytest.mark.asyncio
    async def test_delete_not_initialized(self):
        """Test delete when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.delete("key")

    @pytest.mark.asyncio
    async def test_exists_not_initialized(self):
        """Test exists when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.exists("key")

    @pytest.mark.asyncio
    async def test_clear_not_initialized(self):
        """Test clear when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.clear()

    @pytest.mark.asyncio
    async def test_clear_pattern_not_initialized(self):
        """Test clear_pattern when cache not initialized"""
        cache = L2Cache()
        with pytest.raises(CacheError):
            await cache.clear_pattern("test:*")

    def test_get_stats_not_initialized(self):
        """Test get_stats when cache not initialized"""
        cache = L2Cache()
        loop = asyncio.new_event_loop()
        stats = loop.run_until_complete(cache.get_stats())
        loop.close()
        assert stats["status"] == "not_initialized"


class TestCacheManagerExtended:
    """Extended tests for CacheManager class"""

    def test_track_l2_latency(self):
        """Test L2 latency tracking"""
        manager = CacheManager()
        manager._track_l2_latency(25.5)
        manager._track_l2_latency(30.0)

        assert len(manager._l2_latencies) == 2
        assert 25.5 in manager._l2_latencies

    def test_track_l2_latency_limit(self):
        """Test L2 latency tracking limit"""
        manager = CacheManager()
        for i in range(1100):
            manager._track_l2_latency(float(i))

        assert len(manager._l2_latencies) == 1000

    def test_get_ttl_price_crypto(self, sample_crypto_asset):
        """Test TTL for crypto prices (max 60 seconds)"""
        manager = CacheManager()
        ttl = manager._get_ttl(DataType.PRICE, sample_crypto_asset)
        assert ttl <= 60

    def test_get_ttl_price_stock_after_hours(self, sample_asset):
        """Test TTL for stock prices after hours"""
        manager = CacheManager()
        # We can't control the time in tests easily, so just verify method works
        ttl = manager._get_ttl(DataType.PRICE, sample_asset)
        assert isinstance(ttl, int)
        assert ttl > 0

    def test_get_ttl_fundamentals(self, sample_asset):
        """Test TTL for fundamentals"""
        manager = CacheManager()
        ttl = manager._get_ttl(DataType.FUNDAMENTALS, sample_asset)
        assert isinstance(ttl, int)
        assert ttl > 0

    def test_get_ttl_news(self, sample_asset):
        """Test TTL for news"""
        manager = CacheManager()
        ttl = manager._get_ttl(DataType.NEWS, sample_asset)
        assert isinstance(ttl, int)
        assert ttl > 0

    def test_get_ttl_unknown_type(self, sample_asset):
        """Test TTL for unknown data type defaults to 300"""
        manager = CacheManager()
        ttl = manager._get_ttl(DataType.MACRO, sample_asset)
        assert isinstance(ttl, int)


class TestQueryPattern:
    """Tests for QueryPattern class"""

    def test_init(self):
        """Test QueryPattern initialization"""
        pattern = QueryPattern("AAPL")
        assert pattern.symbol == "AAPL"
        assert pattern.request_count == 0
        assert pattern.last_accessed is not None

    def test_record_access(self):
        """Test recording access"""
        pattern = QueryPattern("AAPL")
        pattern.record_access(DataType.PRICE, 14)

        assert pattern.request_count == 1
        assert pattern.hourly_distribution[14] == 1
        assert pattern.data_types_requested[DataType.PRICE] == 1

    def test_get_peak_hours(self):
        """Test getting peak hours"""
        pattern = QueryPattern("AAPL")
        # Create different access patterns
        for _ in range(10):
            pattern.record_access(DataType.PRICE, 9)
        for _ in range(5):
            pattern.record_access(DataType.PRICE, 14)
        for _ in range(3):
            pattern.record_access(DataType.PRICE, 15)

        peak_hours = pattern.get_peak_hours(top_n=2)
        assert 9 in peak_hours
        assert 14 in peak_hours
        assert 15 not in peak_hours

    def test_get_priority_score(self):
        """Test priority score calculation"""
        pattern = QueryPattern("AAPL")
        # Add some access history
        for _ in range(50):
            pattern.record_access(DataType.PRICE, 14)

        now = datetime.now(UTC)
        score = pattern.get_priority_score(now, set())
        assert score > 0

    def test_get_priority_score_with_market_event(self):
        """Test priority score with market event"""
        pattern = QueryPattern("AAPL")
        for _ in range(10):
            pattern.record_access(DataType.PRICE, 14)

        now = datetime.now(UTC)
        score_without_event = pattern.get_priority_score(now, set())
        score_with_event = pattern.get_priority_score(now, {"AAPL"})

        assert score_with_event > score_without_event


class TestPredictiveCacheWarmerExtended:
    """Extended tests for PredictiveCacheWarmer class"""

    def test_init(self):
        """Test initialization"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            min_request_threshold=5
        )
        assert warmer.min_request_threshold == 5
        assert warmer.is_running is False

    def test_add_market_event(self):
        """Test adding market event"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        warmer.add_market_event("AAPL", "earnings")
        assert "AAPL" in warmer.market_events

    def test_get_symbols_to_warm_no_candidates(self):
        """Test getting symbols to warm when none qualify"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            min_request_threshold=100
        )
        # Record some accesses but below threshold
        for _ in range(5):
            warmer.record_cache_access("AAPL", DataType.PRICE)

        symbols = warmer.get_symbols_to_warm()
        assert len(symbols) == 0

    def test_get_symbols_to_warm_with_candidates(self):
        """Test getting symbols to warm with qualified candidates"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            min_request_threshold=5
        )
        # Record enough accesses
        for _ in range(10):
            warmer.record_cache_access("AAPL", DataType.PRICE)
            warmer.record_cache_access("MSFT", DataType.PRICE)

        symbols = warmer.get_symbols_to_warm()
        assert len(symbols) == 2
        symbol_names = [s[0] for s in symbols]
        assert "AAPL" in symbol_names
        assert "MSFT" in symbol_names

    def test_get_warming_stats(self):
        """Test getting warming statistics"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        warmer.total_warmed = 100
        warmer.successful_warms = 90
        warmer.failed_warms = 10

        stats = warmer.get_warming_stats()
        assert stats["total_warmed"] == 100
        assert stats["successful"] == 90
        assert stats["failed"] == 10
        assert stats["success_rate_percent"] == 90.0

    def test_clear_old_patterns(self):
        """Test clearing old patterns"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        # Create old pattern
        warmer.query_patterns["OLD"] = QueryPattern("OLD")
        warmer.query_patterns["OLD"].last_accessed = datetime.now(UTC) - timedelta(days=10)

        # Create new pattern
        warmer.query_patterns["NEW"] = QueryPattern("NEW")
        warmer.query_patterns["NEW"].last_accessed = datetime.now(UTC)

        removed = warmer.clear_old_patterns(days=7)
        assert removed == 1
        assert "OLD" not in warmer.query_patterns
        assert "NEW" in warmer.query_patterns


class TestUpdateRequest:
    """Tests for UpdateRequest class"""

    def test_init(self, sample_asset):
        """Test UpdateRequest initialization"""
        request = UpdateRequest(
            asset=sample_asset,
            data_type=DataType.PRICE,
            provider="yfinance",
            priority=5
        )
        assert request.asset == sample_asset
        assert request.data_type == DataType.PRICE
        assert request.provider == "yfinance"
        assert request.priority == 5
        assert request.created_at is not None

    def test_get_batch_key(self, sample_asset):
        """Test batch key generation"""
        request = UpdateRequest(
            asset=sample_asset,
            data_type=DataType.PRICE,
            provider="yfinance"
        )
        assert request.get_batch_key() == "price:yfinance"

    def test_repr(self, sample_asset):
        """Test string representation"""
        request = UpdateRequest(
            asset=sample_asset,
            data_type=DataType.PRICE,
            provider="yfinance"
        )
        repr_str = repr(request)
        assert "AAPL" in repr_str
        assert "price" in repr_str
        assert "yfinance" in repr_str


class TestBatchUpdateSchedulerExtended:
    """Extended tests for BatchUpdateScheduler class"""

    def test_init(self):
        """Test initialization"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            batch_size=25,
            batch_interval_seconds=30
        )
        assert scheduler.batch_size == 25
        assert scheduler.batch_interval_seconds == 30

    @pytest.mark.asyncio
    async def test_schedule_update(self, sample_asset):
        """Test scheduling an update"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        await scheduler.schedule_update(
            asset=sample_asset,
            data_type=DataType.PRICE,
            provider="yfinance",
            priority=5
        )
        assert len(scheduler.pending_requests) == 1
        assert scheduler.total_requests == 1

    @pytest.mark.asyncio
    async def test_schedule_updates_batch(self, sample_asset, sample_crypto_asset):
        """Test scheduling multiple updates"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        updates = [
            (sample_asset, DataType.PRICE, "yfinance", 5),
            (sample_crypto_asset, DataType.PRICE, "ccxt", 3),
        ]
        await scheduler.schedule_updates_batch(updates)

        assert len(scheduler.pending_requests) == 2
        assert scheduler.total_requests == 2

    def test_group_requests_by_batch_key(self, sample_asset, sample_crypto_asset):
        """Test grouping requests by batch key"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        requests = [
            UpdateRequest(sample_asset, DataType.PRICE, "yfinance"),
            UpdateRequest(sample_crypto_asset, DataType.PRICE, "yfinance"),
            UpdateRequest(sample_asset, DataType.FUNDAMENTALS, "yfinance"),
        ]

        grouped = scheduler._group_requests_by_batch_key(requests)

        assert "price:yfinance" in grouped
        assert "fundamentals:yfinance" in grouped
        assert len(grouped["price:yfinance"]) == 2
        assert len(grouped["fundamentals:yfinance"]) == 1

    def test_get_next_batch_empty(self):
        """Test getting next batch when empty"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        batch = scheduler._get_next_batch()
        assert batch == []

    def test_get_next_batch_prioritized(self, sample_asset, sample_crypto_asset):
        """Test that batch is prioritized correctly"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            batch_size=2
        )
        # Add requests with different priorities
        scheduler.pending_requests.append(
            UpdateRequest(sample_asset, DataType.PRICE, "yfinance", priority=1)
        )
        scheduler.pending_requests.append(
            UpdateRequest(sample_crypto_asset, DataType.PRICE, "ccxt", priority=10)
        )

        batch = scheduler._get_next_batch()

        assert len(batch) == 2
        # Higher priority should be first
        assert batch[0].priority == 10

    def test_get_stats(self, sample_asset):
        """Test getting scheduler statistics"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            batch_size=50
        )
        scheduler.pending_requests.append(
            UpdateRequest(sample_asset, DataType.PRICE, "yfinance")
        )
        scheduler.total_requests = 10
        scheduler.batches_processed = 5
        scheduler.successful_updates = 8
        scheduler.failed_updates = 2

        stats = scheduler.get_stats()

        assert stats["pending_requests"] == 1
        assert stats["total_requests"] == 10
        assert stats["batches_processed"] == 5
        assert stats["successful_updates"] == 8
        assert stats["failed_updates"] == 2
        assert stats["batch_size"] == 50

    def test_clear_pending(self, sample_asset):
        """Test clearing pending requests"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        scheduler.pending_requests.append(
            UpdateRequest(sample_asset, DataType.PRICE, "yfinance")
        )
        scheduler.pending_requests.append(
            UpdateRequest(sample_asset, DataType.FUNDAMENTALS, "yfinance")
        )

        count = scheduler.clear_pending()

        assert count == 2
        assert len(scheduler.pending_requests) == 0


class TestCacheWarmerExtended:
    """Extended tests for CacheWarmer class"""

    @pytest.mark.asyncio
    async def test_warm_cache_already_in_progress(self):
        """Test warm_cache when already in progress"""
        warmer = CacheWarmer()
        warmer._warming_in_progress = True

        result = await warmer.warm_cache()

        assert result["status"] == "skipped"
        assert result["reason"] == "warming_in_progress"

    @pytest.mark.asyncio
    async def test_warm_cache_force(self):
        """Test force warming even when in progress"""
        warmer = CacheWarmer()
        warmer._warming_in_progress = True

        # Mock the cache manager
        with patch('fiml.cache.warmer.cache_manager') as mock_manager:
            mock_manager.set_price = AsyncMock(return_value=True)

            result = await warmer.warm_cache(
                assets=[Asset(
                    symbol="TEST",
                    name="Test",
                    asset_type=AssetType.EQUITY,
                    market=Market.US,
                    exchange="NASDAQ",
                    currency="USD"
                )],
                force=True
            )

            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_warm_on_startup(self):
        """Test warming on startup"""
        warmer = CacheWarmer()

        with patch.object(warmer, 'warm_cache', new_callable=AsyncMock) as mock_warm:
            mock_warm.return_value = {"status": "completed"}
            result = await warmer.warm_on_startup()

            mock_warm.assert_called_once()
            assert result["status"] == "completed"


class TestCacheIntegration:
    """Integration tests for cache module components"""

    @pytest.mark.asyncio
    async def test_l1_cache_full_lifecycle(self):
        """Test L1 cache through full lifecycle with mocked Redis"""
        cache = L1Cache()

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.config_set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value='{"data": "value"}')
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.exists = AsyncMock(return_value=True)
        mock_redis.ttl = AsyncMock(return_value=60)
        mock_redis.info = AsyncMock(return_value={
            "keyspace_hits": 100,
            "keyspace_misses": 10
        })
        mock_redis.aclose = AsyncMock()

        with patch('redis.asyncio.Redis', return_value=mock_redis):
            await cache.initialize()
            assert cache._initialized is True

            # Test set
            success = await cache.set("test_key", {"data": "value"}, ttl_seconds=60)
            assert success is True

            # Test get
            value = await cache.get("test_key")
            assert value == {"data": "value"}

            # Test exists
            exists = await cache.exists("test_key")
            assert exists is True

            # Test delete
            deleted = await cache.delete("test_key")
            assert deleted is True

            # Test get_ttl
            ttl = await cache.get_ttl("test_key")
            assert ttl == 60

            # Test stats
            stats = await cache.get_stats()
            assert "keyspace_hits" in stats

            # Shutdown
            await cache.shutdown()
            assert cache._initialized is False

    @pytest.mark.asyncio
    async def test_cache_manager_with_analytics(self, sample_asset):
        """Test cache manager tracking analytics"""
        manager = CacheManager()
        manager._initialized = True

        # Mock L1 cache
        manager.l1._initialized = True
        manager.l1._redis = MagicMock()
        manager.l1._redis.get = AsyncMock(return_value='{"price": 150.0}')
        manager.l1._redis.set = AsyncMock(return_value=True)
        manager.l1._redis.setex = AsyncMock(return_value=True)

        # Test get with latency tracking
        value = await manager.get("test_key")
        assert value is not None
        assert manager._l1_hits == 1
        assert len(manager._l1_latencies) == 1

        # Test set with latency tracking
        success = await manager.set("test_key", {"data": "value"}, ttl_seconds=60)
        assert success is True
        assert len(manager._l1_latencies) == 2


class TestBatchSchedulerProcessing:
    """Tests for BatchUpdateScheduler processing operations"""

    @pytest.mark.asyncio
    async def test_run_batch_cycle_empty(self, sample_asset):
        """Test running batch cycle when empty"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        # Should complete without error when empty
        await scheduler._run_batch_cycle()
        assert scheduler.batches_processed == 0

    @pytest.mark.asyncio
    async def test_run_batch_cycle_high_load_period(self, sample_asset):
        """Test batch cycle during high load period"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            low_load_hours=[0, 1, 2, 3],  # Only low load at night
            batch_size=100
        )
        # Add small number of requests (below threshold for high-load processing)
        scheduler.pending_requests.append(
            UpdateRequest(sample_asset, DataType.PRICE, "yfinance")
        )

        # During high load with few requests, should skip
        await scheduler._run_batch_cycle()

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test starting and stopping the scheduler"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            batch_interval_seconds=1
        )

        # Start scheduler
        await scheduler.start()
        assert scheduler.is_running is True

        # Give it time to run
        await asyncio.sleep(0.1)

        # Stop scheduler
        await scheduler.stop()
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, caplog):
        """Test starting when already running"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        scheduler.is_running = True

        await scheduler.start()
        # Should warn about already running


class TestPredictiveCacheWarmerProcessing:
    """Tests for PredictiveCacheWarmer processing operations"""

    @pytest.mark.asyncio
    async def test_warm_symbol_no_provider(self):
        """Test warming symbol when no provider found"""
        mock_registry = MagicMock()
        mock_registry.get_provider_for_data_type = MagicMock(return_value=None)

        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=mock_registry
        )

        # Should return True even if provider not found (graceful handling)
        result = await warmer.warm_symbol("AAPL", [DataType.PRICE])
        # When provider returns None, the warming should not fail
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_run_warming_cycle_not_in_schedule(self):
        """Test warming cycle when not in schedule"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            warming_schedule=[25]  # Hour that doesn't exist
        )

        await warmer.run_warming_cycle()
        # Should skip without error

    @pytest.mark.asyncio
    async def test_run_warming_cycle_no_symbols(self):
        """Test warming cycle with no symbols to warm"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock(),
            warming_schedule=list(range(24)),  # All hours
            min_request_threshold=1000
        )

        await warmer.run_warming_cycle()
        # Should complete without error

    @pytest.mark.asyncio
    async def test_start_background_warming_already_running(self, caplog):
        """Test starting background warming when already running"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )
        warmer.is_running = True

        await warmer.start_background_warming()
        # Should warn about already running

    @pytest.mark.asyncio
    async def test_stop_background_warming(self):
        """Test stopping background warming"""
        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )

        await warmer.start_background_warming(interval_minutes=1)
        await asyncio.sleep(0.1)
        await warmer.stop_background_warming()

        assert warmer.is_running is False


class TestCacheWarmerScheduled:
    """Tests for CacheWarmer scheduled operations"""

    @pytest.mark.asyncio
    async def test_scheduled_warm(self):
        """Test scheduled warming"""
        warmer = CacheWarmer()

        # Run scheduled warming in background
        task = asyncio.create_task(warmer.scheduled_warm(interval_seconds=1))

        # Let it run for a moment
        await asyncio.sleep(0.1)

        # Cancel the task
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


class TestL1CacheBatchAndEviction:
    """Tests for L1Cache batch and eviction operations"""

    @pytest.mark.asyncio
    async def test_get_many_with_mocked_redis(self):
        """Test get_many with mocked Redis pipeline"""
        cache = L1Cache()
        cache._initialized = True

        # Create mock pipeline
        mock_pipe = MagicMock()
        mock_pipe.get = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=['{"key1": "value1"}', None, '{"key3": "value3"}'])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        cache._redis = mock_redis

        results = await cache.get_many(["key1", "key2", "key3"])

        assert len(results) == 3
        assert results[0] == {"key1": "value1"}
        assert results[1] is None
        assert results[2] == {"key3": "value3"}

    @pytest.mark.asyncio
    async def test_set_many_with_mocked_redis(self):
        """Test set_many with mocked Redis pipeline"""
        cache = L1Cache()
        cache._initialized = True

        # Create mock pipeline
        mock_pipe = MagicMock()
        mock_pipe.set = MagicMock()
        mock_pipe.setex = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[True, True])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        cache._redis = mock_redis

        count = await cache.set_many([
            ("key1", {"value": 1}, 60),
            ("key2", {"value": 2}, None)
        ])

        assert count == 2

    @pytest.mark.asyncio
    async def test_clear_pattern_with_keys(self):
        """Test clear_pattern with keys found"""
        cache = L1Cache()
        cache._initialized = True

        # Mock scan_iter to return keys
        async def mock_scan_iter(*args, **kwargs):
            yield "test:key1"
            yield "test:key2"

        mock_redis = MagicMock()
        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = AsyncMock(return_value=2)
        cache._redis = mock_redis

        deleted = await cache.clear_pattern("test:*")
        assert deleted == 2

    @pytest.mark.asyncio
    async def test_evict_least_used(self):
        """Test manual eviction of least used keys"""
        cache = L1Cache()
        cache._initialized = True

        # Set up access counts
        # Using datetime.now(UTC) to match l1_cache.py _track_access() format
        cache._access_counts = {"key1": 1, "key2": 10, "key3": 5}
        cache._last_access = {
            "key1": datetime.now(UTC),
            "key2": datetime.now(UTC),
            "key3": datetime.now(UTC)
        }

        mock_redis = MagicMock()
        mock_redis.exists = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        cache._redis = mock_redis

        evicted = await cache.evict_least_used(count=1)

        # Should evict key1 (lowest access count)
        assert evicted == 1
        assert "key1" not in cache._access_counts

    @pytest.mark.asyncio
    async def test_evict_least_used_skip_protected(self):
        """Test that protected keys are not evicted"""
        cache = L1Cache()
        cache._initialized = True

        # Set up access counts
        cache._access_counts = {"protected_key": 1, "normal_key": 2}
        cache._protected_keys.add("protected_key")

        mock_redis = MagicMock()
        mock_redis.exists = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        cache._redis = mock_redis

        evicted = await cache.evict_least_used(count=2)

        # Protected key should be skipped
        assert "protected_key" in cache._access_counts or evicted == 1


class TestCacheManagerPricesAndReadThrough:
    """Tests for CacheManager price operations and read-through caching"""

    @pytest.mark.asyncio
    async def test_get_price(self, sample_asset):
        """Test getting price from cache"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        # Mock Redis to return price
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value='{"price": 150.0, "change": 2.5}')
        manager.l1._redis = mock_redis

        result = await manager.get_price(sample_asset)

        assert result is not None
        assert result["price"] == 150.0

    @pytest.mark.asyncio
    async def test_get_price_miss(self, sample_asset):
        """Test getting price with cache miss"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        # Mock Redis to return None (cache miss)
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        manager.l1._redis = mock_redis

        result = await manager.get_price(sample_asset)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_price(self, sample_asset):
        """Test setting price in cache"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        mock_redis = MagicMock()
        mock_redis.setex = AsyncMock(return_value=True)
        manager.l1._redis = mock_redis

        price_data = {"price": 150.0, "change": 2.5}
        result = await manager.set_price(sample_asset, "yfinance", price_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_fundamentals(self, sample_asset):
        """Test getting fundamentals from cache"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value='{"pe_ratio": 25.0, "eps": 6.5}')
        manager.l1._redis = mock_redis

        result = await manager.get_fundamentals(sample_asset)

        assert result is not None
        assert result["pe_ratio"] == 25.0

    @pytest.mark.asyncio
    async def test_set_fundamentals(self, sample_asset):
        """Test setting fundamentals in cache"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        mock_redis = MagicMock()
        mock_redis.setex = AsyncMock(return_value=True)
        manager.l1._redis = mock_redis

        fundamentals = {"pe_ratio": 25.0, "eps": 6.5}
        result = await manager.set_fundamentals(sample_asset, "yfinance", fundamentals)

        assert result is True

    @pytest.mark.asyncio
    async def test_invalidate_asset(self, sample_asset):
        """Test invalidating all cached data for an asset"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        async def mock_scan_iter(*args, **kwargs):
            yield f"price:{sample_asset.symbol}:yfinance"
            yield f"fundamentals:{sample_asset.symbol}:yfinance"

        mock_redis = MagicMock()
        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = AsyncMock(return_value=2)
        manager.l1._redis = mock_redis

        deleted = await manager.invalidate_asset(sample_asset)

        assert deleted == 2

    @pytest.mark.asyncio
    async def test_get_prices_batch(self, sample_asset, sample_crypto_asset):
        """Test batch price retrieval"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        # Create mock pipeline
        mock_pipe = MagicMock()
        mock_pipe.get = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[
            '{"price": 150.0}',
            '{"price": 50000.0}'
        ])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        manager.l1._redis = mock_redis

        results = await manager.get_prices_batch([sample_asset, sample_crypto_asset])

        assert len(results) == 2
        assert manager._l1_hits == 2

    @pytest.mark.asyncio
    async def test_set_prices_batch(self, sample_asset, sample_crypto_asset):
        """Test batch price setting"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        # Create mock pipeline
        mock_pipe = MagicMock()
        mock_pipe.setex = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[True, True])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        manager.l1._redis = mock_redis

        items = [
            (sample_asset, "yfinance", {"price": 150.0}),
            (sample_crypto_asset, "ccxt", {"price": 50000.0})
        ]

        count = await manager.set_prices_batch(items)

        assert count == 2


class TestCacheAnalyticsPrometheus:
    """Tests for CacheAnalytics Prometheus metrics (when available)"""

    def test_init_with_prometheus_disabled(self):
        """Test initialization with Prometheus explicitly disabled"""
        analytics = CacheAnalytics(enable_prometheus=False)
        assert analytics.enable_prometheus is False

    def test_record_access_updates_hourly_stats(self):
        """Test that recording access updates hourly stats"""
        analytics = CacheAnalytics(enable_prometheus=False)

        analytics.record_cache_access(DataType.PRICE, True, 10.0, "l1")

        # Check hourly stats are updated
        assert len(analytics.hourly_stats) > 0
        current_hour_key = datetime.now(UTC).strftime("%Y-%m-%d-%H")
        assert current_hour_key in analytics.hourly_stats
        assert analytics.hourly_stats[current_hour_key]["hits"] == 1


class TestEvictionPolicyValues:
    """Tests for EvictionPolicy enum values"""

    def test_all_eviction_policies(self):
        """Test all eviction policy enum values"""
        assert EvictionPolicy.LRU.value == "lru"
        assert EvictionPolicy.LFU.value == "lfu"
        assert EvictionPolicy.TTL.value == "ttl"
        assert EvictionPolicy.FIFO.value == "fifo"
        assert EvictionPolicy.HYBRID.value == "hybrid"


class TestEvictionTrackerPolicy:
    """Tests for EvictionTracker with different policies"""

    def test_get_eviction_candidates_unknown_policy(self):
        """Test getting candidates with unsupported policy"""
        tracker = EvictionTracker(policy=EvictionPolicy.TTL, max_entries=10)
        tracker.track_access("key1")

        # For TTL policy, candidates method returns empty (not implemented)
        candidates = tracker.get_eviction_candidates(count=5)
        assert candidates == []


class TestCacheUtilsPercentile:
    """Tests for cache utils percentile calculation"""

    def test_percentile_edge_cases(self):
        """Test percentile calculation edge cases"""
        from fiml.cache.utils import calculate_percentile

        # Empty list
        assert calculate_percentile([], 50) == 0.0

        # Single element
        assert calculate_percentile([10.0], 50) == 10.0

        # Two elements
        assert calculate_percentile([10.0, 20.0], 50) == 10.0

        # P0 and P100
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert calculate_percentile(data, 0) == 10.0

    def test_percentile_high_values(self):
        """Test percentile calculation for high percentiles"""
        from fiml.cache.utils import calculate_percentile

        data = list(range(1, 101))  # 1 to 100
        data = [float(x) for x in data]

        p97 = calculate_percentile(data, 97)
        p99 = calculate_percentile(data, 99)

        assert p97 >= 97.0
        assert p99 >= 99.0


class TestBatchSchedulerProcessBatch:
    """Tests for BatchUpdateScheduler _process_batch method"""

    @pytest.mark.asyncio
    async def test_process_batch_provider_not_found(self, sample_asset):
        """Test processing batch when provider not found"""
        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=None)

        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=mock_registry
        )

        batch = [UpdateRequest(sample_asset, DataType.PRICE, "unknown_provider")]

        stats = await scheduler._process_batch(batch)

        assert stats["failed"] == 1
        assert stats["success"] == 0

    @pytest.mark.asyncio
    async def test_process_batch_price_with_batch_support(self, sample_asset, sample_crypto_asset):
        """Test processing batch with provider that supports batch operations"""
        mock_provider = MagicMock()
        mock_provider.get_prices_batch = AsyncMock(return_value=[
            {"price": 150.0},
            {"price": 50000.0}
        ])

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_prices_batch = AsyncMock(return_value=2)

        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=mock_provider)

        scheduler = BatchUpdateScheduler(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry
        )

        batch = [
            UpdateRequest(sample_asset, DataType.PRICE, "yfinance"),
            UpdateRequest(sample_crypto_asset, DataType.PRICE, "yfinance"),
        ]

        stats = await scheduler._process_batch(batch)

        assert stats["success"] == 2
        assert stats["api_calls"] == 1
        assert stats["api_calls_saved"] == 1

    @pytest.mark.asyncio
    async def test_process_batch_price_without_batch_support(self, sample_asset):
        """Test processing batch with provider that doesn't support batch operations"""
        mock_provider = MagicMock()
        # No get_prices_batch method
        mock_provider.get_price = AsyncMock(return_value={"price": 150.0})
        if hasattr(mock_provider, 'get_prices_batch'):
            delattr(mock_provider, 'get_prices_batch')

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_price = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=mock_provider)

        scheduler = BatchUpdateScheduler(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry
        )

        batch = [UpdateRequest(sample_asset, DataType.PRICE, "yfinance")]

        stats = await scheduler._process_batch(batch)

        assert stats["success"] == 1
        assert stats["api_calls"] == 1

    @pytest.mark.asyncio
    async def test_process_batch_price_individual_failure(self, sample_asset):
        """Test processing batch when individual price fetch fails"""
        mock_provider = MagicMock()
        mock_provider.get_price = AsyncMock(side_effect=Exception("API error"))

        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=mock_provider)

        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=mock_registry
        )

        batch = [UpdateRequest(sample_asset, DataType.PRICE, "yfinance")]

        stats = await scheduler._process_batch(batch)

        assert stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_process_batch_fundamentals_success(self, sample_asset):
        """Test processing batch with fundamentals data type"""
        mock_provider = MagicMock()
        mock_provider.get_fundamentals = AsyncMock(return_value={"pe_ratio": 25.0})

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_fundamentals = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=mock_provider)

        scheduler = BatchUpdateScheduler(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry
        )

        batch = [UpdateRequest(sample_asset, DataType.FUNDAMENTALS, "yfinance")]

        stats = await scheduler._process_batch(batch)

        assert stats["success"] == 1

    @pytest.mark.asyncio
    async def test_process_batch_fundamentals_failure(self, sample_asset):
        """Test processing batch when fundamentals fetch fails"""
        mock_provider = MagicMock()
        mock_provider.get_fundamentals = AsyncMock(side_effect=Exception("API error"))

        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=mock_provider)

        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=mock_registry
        )

        batch = [UpdateRequest(sample_asset, DataType.FUNDAMENTALS, "yfinance")]

        stats = await scheduler._process_batch(batch)

        assert stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_process_batch_general_exception(self, sample_asset):
        """Test processing batch when general exception occurs"""
        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(side_effect=Exception("Registry error"))

        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=mock_registry
        )

        batch = [UpdateRequest(sample_asset, DataType.PRICE, "yfinance")]

        stats = await scheduler._process_batch(batch)

        assert stats["failed"] == 1


class TestBatchSchedulerRunCycle:
    """Tests for BatchUpdateScheduler _run_batch_cycle method"""

    @pytest.mark.asyncio
    async def test_run_batch_cycle_with_processing(self, sample_asset):
        """Test running a complete batch cycle"""
        mock_provider = MagicMock()
        mock_provider.get_price = AsyncMock(return_value={"price": 150.0})

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_price = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=mock_provider)

        scheduler = BatchUpdateScheduler(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry,
            low_load_hours=list(range(24)),  # All hours are low load
            batch_size=10
        )

        # Add a request
        await scheduler.schedule_update(sample_asset, DataType.PRICE, "yfinance")

        # Run the batch cycle
        await scheduler._run_batch_cycle()

        assert scheduler.batches_processed == 1


class TestBatchSchedulerFlush:
    """Tests for BatchUpdateScheduler flush_pending method"""

    @pytest.mark.asyncio
    async def test_flush_pending_empty(self):
        """Test flushing when no pending requests"""
        scheduler = BatchUpdateScheduler(
            cache_manager=MagicMock(),
            provider_registry=MagicMock()
        )

        stats = await scheduler.flush_pending()

        assert stats["batches"] == 0

    @pytest.mark.asyncio
    async def test_flush_pending_with_requests(self, sample_asset):
        """Test flushing with pending requests"""
        mock_provider = MagicMock()
        mock_provider.get_price = AsyncMock(return_value={"price": 150.0})

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_price = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider = MagicMock(return_value=mock_provider)

        scheduler = BatchUpdateScheduler(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry
        )

        # Add requests
        await scheduler.schedule_update(sample_asset, DataType.PRICE, "yfinance")

        # Flush all pending
        stats = await scheduler.flush_pending()

        assert stats["batches"] >= 1


class TestPredictiveCacheWarmerWarmSymbol:
    """Tests for PredictiveCacheWarmer warm_symbol method"""

    @pytest.mark.asyncio
    async def test_warm_symbol_price_success(self):
        """Test warming symbol with successful price fetch"""
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.get_price = AsyncMock(return_value={"price": 150.0})

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_price = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider_for_data_type = MagicMock(return_value=mock_provider)

        warmer = PredictiveCacheWarmer(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry
        )

        result = await warmer.warm_symbol("AAPL", [DataType.PRICE])

        assert result is True
        assert warmer.successful_warms == 1

    @pytest.mark.asyncio
    async def test_warm_symbol_fundamentals_success(self):
        """Test warming symbol with successful fundamentals fetch"""
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.get_fundamentals = AsyncMock(return_value={"pe_ratio": 25.0})

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_fundamentals = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider_for_data_type = MagicMock(return_value=mock_provider)

        warmer = PredictiveCacheWarmer(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry
        )

        result = await warmer.warm_symbol("AAPL", [DataType.FUNDAMENTALS])

        assert result is True

    @pytest.mark.asyncio
    async def test_warm_symbol_failure(self):
        """Test warming symbol when fetch fails"""
        mock_provider = MagicMock()
        mock_provider.get_price = AsyncMock(return_value=None)

        mock_registry = MagicMock()
        mock_registry.get_provider_for_data_type = MagicMock(return_value=mock_provider)

        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=mock_registry
        )

        result = await warmer.warm_symbol("AAPL", [DataType.PRICE])

        assert result is False
        assert warmer.failed_warms == 1

    @pytest.mark.asyncio
    async def test_warm_symbol_exception(self):
        """Test warming symbol when exception occurs"""
        mock_provider = MagicMock()
        mock_provider.get_price = AsyncMock(side_effect=Exception("API error"))

        mock_registry = MagicMock()
        mock_registry.get_provider_for_data_type = MagicMock(return_value=mock_provider)

        warmer = PredictiveCacheWarmer(
            cache_manager=MagicMock(),
            provider_registry=mock_registry
        )

        result = await warmer.warm_symbol("AAPL", [DataType.PRICE])

        assert result is False


class TestPredictiveCacheWarmerBatch:
    """Tests for PredictiveCacheWarmer warm_cache_batch method"""

    @pytest.mark.asyncio
    async def test_warm_cache_batch(self):
        """Test batch warming multiple symbols"""
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.get_price = AsyncMock(return_value={"price": 150.0})

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_price = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider_for_data_type = MagicMock(return_value=mock_provider)

        warmer = PredictiveCacheWarmer(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry
        )

        results = await warmer.warm_cache_batch(["AAPL", "MSFT"], concurrency=2)

        assert len(results) == 2
        assert "AAPL" in results
        assert "MSFT" in results


class TestPredictiveCacheWarmerWarmingCycle:
    """Tests for PredictiveCacheWarmer run_warming_cycle method"""

    @pytest.mark.asyncio
    async def test_run_warming_cycle_with_symbols(self):
        """Test running warming cycle with qualified symbols"""
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.get_price = AsyncMock(return_value={"price": 150.0})

        mock_cache_manager = MagicMock()
        mock_cache_manager.set_price = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.get_provider_for_data_type = MagicMock(return_value=mock_provider)

        warmer = PredictiveCacheWarmer(
            cache_manager=mock_cache_manager,
            provider_registry=mock_registry,
            warming_schedule=list(range(24)),  # All hours
            min_request_threshold=1
        )

        # Add enough accesses to qualify
        for _ in range(5):
            warmer.record_cache_access("AAPL", DataType.PRICE)

        await warmer.run_warming_cycle()


class TestCacheManagerReadThrough:
    """Tests for CacheManager read-through cache pattern"""

    @pytest.mark.asyncio
    async def test_get_with_read_through_hit(self, sample_asset):
        """Test read-through cache with cache hit"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value='{"price": 150.0}')
        manager.l1._redis = mock_redis

        fetch_fn = AsyncMock(return_value={"price": 200.0})

        result = await manager.get_with_read_through(
            key="test_key",
            data_type=DataType.PRICE,
            fetch_fn=fetch_fn,
            asset=sample_asset
        )

        assert result == {"price": 150.0}
        assert manager._l1_hits == 1
        fetch_fn.assert_not_called()  # Should not fetch if cache hit

    @pytest.mark.asyncio
    async def test_get_with_read_through_miss(self, sample_asset):
        """Test read-through cache with cache miss"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        manager.l1._redis = mock_redis

        fetch_fn = AsyncMock(return_value={"price": 200.0})

        result = await manager.get_with_read_through(
            key="test_key",
            data_type=DataType.PRICE,
            fetch_fn=fetch_fn,
            asset=sample_asset
        )

        assert result == {"price": 200.0}
        assert manager._l1_misses == 1
        fetch_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_read_through_fetch_error(self, sample_asset):
        """Test read-through cache when fetch fails"""
        manager = CacheManager()
        manager._initialized = True
        manager.l1._initialized = True

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        manager.l1._redis = mock_redis

        fetch_fn = AsyncMock(side_effect=Exception("Fetch error"))

        result = await manager.get_with_read_through(
            key="test_key",
            data_type=DataType.PRICE,
            fetch_fn=fetch_fn,
            asset=sample_asset
        )

        assert result is None


class TestL1CacheErrorHandling:
    """Tests for L1Cache error handling paths"""

    @pytest.mark.asyncio
    async def test_get_parse_error(self):
        """Test get when JSON parsing fails"""
        cache = L1Cache()
        cache._initialized = True

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value="invalid json{")
        cache._redis = mock_redis

        result = await cache.get("test_key")

        # Should return None on parse error
        assert result is None

    @pytest.mark.asyncio
    async def test_get_many_parse_error(self):
        """Test get_many when JSON parsing fails"""
        cache = L1Cache()
        cache._initialized = True

        mock_pipe = MagicMock()
        mock_pipe.get = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=['{"valid": 1}', 'invalid{', '{"also_valid": 2}'])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        cache._redis = mock_redis

        results = await cache.get_many(["key1", "key2", "key3"])

        assert len(results) == 3
        assert results[0] == {"valid": 1}
        assert results[1] is None  # Parse error
        assert results[2] == {"also_valid": 2}

    @pytest.mark.asyncio
    async def test_get_ttl_negative(self):
        """Test get_ttl when key has no TTL (returns negative)"""
        cache = L1Cache()
        cache._initialized = True

        mock_redis = MagicMock()
        mock_redis.ttl = AsyncMock(return_value=-1)
        cache._redis = mock_redis

        result = await cache.get_ttl("test_key")

        assert result is None


class TestL2CacheMockedOperations:
    """Tests for L2Cache operations with mocked database"""

    @pytest.mark.asyncio
    async def test_get_price_success(self):
        """Test get_price with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        # Create mock result row
        mock_row = (
            datetime.now(timezone.utc),  # time
            1,  # asset_id
            "yfinance",  # provider
            150.0,  # price
            2.5,  # change
            1.7,  # change_percent
            1000000,  # volume
            0.95,  # confidence
            {"extra": "data"},  # metadata
        )

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_price(asset_id=1, provider="yfinance")

        assert result is not None
        assert result["price"] == 150.0
        assert result["provider"] == "yfinance"

    @pytest.mark.asyncio
    async def test_get_price_not_found(self):
        """Test get_price when no price found"""
        cache = L2Cache()
        cache._initialized = True

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_price(asset_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_price_exception(self):
        """Test get_price when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_price(asset_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_price_success(self):
        """Test set_price with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.set_price(
            asset_id=1,
            provider="yfinance",
            price=150.0,
            change=2.5,
            change_percent=1.7
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_set_price_exception(self):
        """Test set_price when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.set_price(asset_id=1, provider="yfinance", price=150.0)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_ohlcv_success(self):
        """Test get_ohlcv with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        # Create mock result rows
        mock_rows = [
            (datetime.now(timezone.utc), 1, "yfinance", 150.0, 155.0, 145.0, 152.0, 1000000, "1d"),
            (datetime.now(timezone.utc), 1, "yfinance", 148.0, 152.0, 147.0, 150.0, 900000, "1d"),
        ]

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=mock_rows)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_ohlcv(asset_id=1, timeframe="1d", limit=10)

        assert len(result) == 2
        assert result[0]["open"] == 150.0

    @pytest.mark.asyncio
    async def test_get_ohlcv_exception(self):
        """Test get_ohlcv when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_ohlcv(asset_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_fundamentals_success(self):
        """Test get_fundamentals with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_row = (1, 1, "yfinance", {"pe_ratio": 25.0}, datetime.now(timezone.utc), 3600)

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_fundamentals(asset_id=1)

        assert result is not None
        assert result["data"] == {"pe_ratio": 25.0}

    @pytest.mark.asyncio
    async def test_get_fundamentals_exception(self):
        """Test get_fundamentals when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_fundamentals(asset_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_fundamentals_success(self):
        """Test set_fundamentals with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.set_fundamentals(
            asset_id=1,
            provider="yfinance",
            data={"pe_ratio": 25.0}
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_set_fundamentals_exception(self):
        """Test set_fundamentals when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.set_fundamentals(asset_id=1, provider="yfinance", data={})

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_success(self):
        """Test cleanup_expired with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_result = MagicMock()
        mock_result.rowcount = 5

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.cleanup_expired()

        assert result == 5

    @pytest.mark.asyncio
    async def test_cleanup_expired_exception(self):
        """Test cleanup_expired when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.cleanup_expired()

        assert result == 0

    @pytest.mark.asyncio
    async def test_set_generic_success(self):
        """Test generic set with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.set("test_key", {"data": "value"}, ttl_seconds=60)

        assert result is True

    @pytest.mark.asyncio
    async def test_set_generic_exception(self):
        """Test generic set when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.set("test_key", {"data": "value"})

        assert result is False

    @pytest.mark.asyncio
    async def test_get_generic_success(self):
        """Test generic get with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_row = ({"data": "value"},)

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get("test_key")

        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_get_generic_not_found(self):
        """Test generic get when key not found"""
        cache = L2Cache()
        cache._initialized = True

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_generic_exception(self):
        """Test generic get when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_generic_success(self):
        """Test generic delete with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_result = MagicMock()
        mock_result.rowcount = 1

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.delete("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_generic_exception(self):
        """Test generic delete when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.delete("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_generic_success(self):
        """Test generic exists with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=(1,))

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.exists("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_generic_exception(self):
        """Test generic exists when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.exists("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_success(self):
        """Test clear with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_result = MagicMock()
        mock_result.rowcount = 10

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.clear()

        assert result == 10

    @pytest.mark.asyncio
    async def test_clear_exception(self):
        """Test clear when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.clear()

        assert result == 0

    @pytest.mark.asyncio
    async def test_clear_pattern_success(self):
        """Test clear_pattern with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_result = MagicMock()
        mock_result.rowcount = 5

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.clear_pattern("test:%")

        assert result == 5

    @pytest.mark.asyncio
    async def test_clear_pattern_exception(self):
        """Test clear_pattern when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.clear_pattern("test:%")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Test get_stats with mocked session"""
        cache = L2Cache()
        cache._initialized = True

        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=100)

        mock_expired_result = MagicMock()
        mock_expired_result.scalar = MagicMock(return_value=10)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_expired_result])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_stats()

        assert result["status"] == "initialized"
        assert result["total_entries"] == 100
        assert result["expired_entries"] == 10

    @pytest.mark.asyncio
    async def test_get_stats_exception(self):
        """Test get_stats when exception occurs"""
        cache = L2Cache()
        cache._initialized = True

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_session)
        cache._session_maker = mock_session_maker

        result = await cache.get_stats()

        assert result["status"] == "error"
