"""
Cache module - Multi-layer caching system with advanced optimizations

Components:
- L1 Cache: Redis with LRU/LFU/Hybrid eviction (10-100ms target)
- L2 Cache: PostgreSQL + TimescaleDB (300-700ms target)
- Cache Manager: Coordinates L1/L2 with intelligent TTL and read-through caching
- Predictive Warmer: Pre-fetches based on query patterns
- Batch Scheduler: Groups and schedules cache updates
- Analytics: Comprehensive performance monitoring with Prometheus metrics
- Utils: Shared utilities
"""

from fiml.cache.analytics import CacheAnalytics, cache_analytics
from fiml.cache.eviction import EvictionPolicy, EvictionTracker, eviction_tracker
from fiml.cache.l1_cache import L1Cache, l1_cache
from fiml.cache.l2_cache import L2Cache, l2_cache
from fiml.cache.manager import CacheManager, cache_manager
from fiml.cache.scheduler import BatchUpdateScheduler, UpdateRequest
from fiml.cache.utils import calculate_percentile
from fiml.cache.warmer import CacheWarmer, cache_warmer
from fiml.cache.warming import PredictiveCacheWarmer, QueryPattern

__all__ = [
    # Core caching
    "L1Cache",
    "l1_cache",
    "L2Cache",
    "l2_cache",
    "CacheManager",
    "cache_manager",
    # Legacy warmer
    "CacheWarmer",
    "cache_warmer",
    # Advanced features
    "PredictiveCacheWarmer",
    "QueryPattern",
    "BatchUpdateScheduler",
    "UpdateRequest",
    "CacheAnalytics",
    "cache_analytics",
    # Eviction
    "EvictionTracker",
    "EvictionPolicy",
    "eviction_tracker",
    # Utils
    "calculate_percentile",
]
