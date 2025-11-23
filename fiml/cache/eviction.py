"""
Cache Eviction Policies

Implements intelligent cache eviction strategies:
- LRU (Least Recently Used)
- LFU (Least Frequently Used)
- TTL-based eviction
- Memory pressure-based eviction
"""

import time
from collections import OrderedDict
from enum import Enum
from typing import Any, Dict, List, Optional

from fiml.core.logging import get_logger

logger = get_logger(__name__)

# Memory pressure threshold constant
DEFAULT_MEMORY_PRESSURE_THRESHOLD = 0.9  # 90%


class EvictionPolicy(str, Enum):
    """Cache eviction policy types"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out
    HYBRID = "hybrid"  # Combination of LRU and LFU


class EvictionTracker:
    """
    Tracks access patterns for intelligent cache eviction

    Features:
    - Access time tracking (LRU)
    - Access frequency tracking (LFU)
    - Memory pressure monitoring
    - Eviction statistics
    """

    def __init__(self, policy: EvictionPolicy = EvictionPolicy.LRU, max_entries: int = 10000):
        self.policy = policy
        self.max_entries = max_entries

        # LRU tracking - OrderedDict maintains insertion/access order
        self._lru_tracker: OrderedDict[str, float] = OrderedDict()

        # LFU tracking - access counts
        self._lfu_tracker: Dict[str, int] = {}

        # Statistics
        self._evictions = 0
        self._total_accesses = 0

    def track_access(self, key: str) -> None:
        """
        Track cache key access for eviction policy

        Args:
            key: Cache key that was accessed
        """
        self._total_accesses += 1
        current_time = time.time()

        if self.policy == EvictionPolicy.LRU:
            # Move to end (most recently used)
            if key in self._lru_tracker:
                del self._lru_tracker[key]
            self._lru_tracker[key] = current_time

            # Limit size
            if len(self._lru_tracker) > self.max_entries:
                # Remove oldest
                oldest_key = next(iter(self._lru_tracker))
                del self._lru_tracker[oldest_key]
                self._evictions += 1

        elif self.policy == EvictionPolicy.LFU:
            # Increment access count
            self._lfu_tracker[key] = self._lfu_tracker.get(key, 0) + 1

            # Limit size by removing least frequently used
            if len(self._lfu_tracker) > self.max_entries:
                # Find key with minimum access count
                min_key = min(self._lfu_tracker, key=lambda k: self._lfu_tracker.get(k, 0))
                del self._lfu_tracker[min_key]
                self._evictions += 1

    def should_evict(self, current_size: int, max_size: int, threshold: Optional[float] = None) -> bool:
        """
        Determine if eviction should occur based on memory pressure

        Args:
            current_size: Current cache size
            max_size: Maximum cache size
            threshold: Memory pressure threshold (0.0-1.0), defaults to 0.9

        Returns:
            True if eviction should occur
        """
        if threshold is None:
            threshold = DEFAULT_MEMORY_PRESSURE_THRESHOLD
        return current_size >= (max_size * threshold)

    def get_eviction_candidates(self, count: int = 10) -> List[str]:
        """
        Get list of cache keys that are candidates for eviction

        Args:
            count: Number of candidates to return

        Returns:
            List of cache keys to evict
        """
        if self.policy == EvictionPolicy.LRU:
            # Return oldest accessed keys
            candidates = list(self._lru_tracker.keys())[:count]
            return candidates

        elif self.policy == EvictionPolicy.LFU:
            # Return least frequently accessed keys
            sorted_keys = sorted(self._lfu_tracker.items(), key=lambda x: x[1])
            candidates = [key for key, _ in sorted_keys[:count]]
            return candidates

        return []

    def remove_key(self, key: str) -> None:
        """
        Remove key from tracking

        Args:
            key: Cache key to remove
        """
        if key in self._lru_tracker:
            del self._lru_tracker[key]

        if key in self._lfu_tracker:
            del self._lfu_tracker[key]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get eviction tracker statistics

        Returns:
            Statistics dictionary
        """
        return {
            "policy": self.policy.value,
            "max_entries": self.max_entries,
            "tracked_keys": len(self._lru_tracker) if self.policy == EvictionPolicy.LRU else len(self._lfu_tracker),
            "total_evictions": self._evictions,
            "total_accesses": self._total_accesses,
        }

    def get_access_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get access information for a specific key

        Args:
            key: Cache key

        Returns:
            Access information or None
        """
        if self.policy == EvictionPolicy.LRU:
            if key in self._lru_tracker:
                return {
                    "last_access_time": self._lru_tracker[key],
                    "age_seconds": time.time() - self._lru_tracker[key]
                }

        elif self.policy == EvictionPolicy.LFU:
            if key in self._lfu_tracker:
                return {
                    "access_count": self._lfu_tracker[key]
                }

        return None

    def clear(self) -> None:
        """Clear all tracking data"""
        self._lru_tracker.clear()
        self._lfu_tracker.clear()
        self._evictions = 0
        self._total_accesses = 0


# Global eviction tracker instance
eviction_tracker = EvictionTracker(policy=EvictionPolicy.LRU, max_entries=10000)
