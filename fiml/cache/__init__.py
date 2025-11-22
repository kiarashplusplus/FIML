"""
Cache module - Multi-layer caching system

Components:
- L1 Cache: Redis (10-100ms target)
- L2 Cache: PostgreSQL + TimescaleDB (300-700ms target)
- Cache Manager: Coordinates L1/L2 with fallback
- Cache Warmer: Proactive data loading
- Eviction Tracker: Intelligent eviction policies
- Utils: Shared utilities
"""

from fiml.cache.l1_cache import L1Cache, l1_cache
from fiml.cache.l2_cache import L2Cache, l2_cache
from fiml.cache.manager import CacheManager, cache_manager
from fiml.cache.warmer import CacheWarmer, cache_warmer
from fiml.cache.eviction import EvictionTracker, EvictionPolicy, eviction_tracker
from fiml.cache.utils import calculate_percentile

__all__ = [
    "L1Cache",
    "l1_cache",
    "L2Cache",
    "l2_cache",
    "CacheManager",
    "cache_manager",
    "CacheWarmer",
    "cache_warmer",
    "EvictionTracker",
    "EvictionPolicy",
    "eviction_tracker",
    "calculate_percentile",
]
