"""
L1 Cache - Redis In-Memory Cache
Target: 10-100ms latency
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import redis.asyncio as redis

from fiml.cache.eviction import EvictionPolicy
from fiml.core.config import settings
from fiml.core.exceptions import CacheError
from fiml.core.logging import get_logger

logger = get_logger(__name__)


class L1Cache:
    """
    Redis-based L1 cache for ultra-fast data access

    Features:
    - 10-100ms latency target
    - Automatic TTL management
    - JSON serialization
    - Connection pooling
    - LFU/LRU/Hybrid eviction policies
    - Protected keys (never evicted)
    - Access frequency tracking
    """

    def __init__(
        self,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        protected_patterns: Optional[List[str]] = None
    ) -> None:
        self._redis: Optional[redis.Redis] = None
        self._initialized = False
        self.eviction_policy = eviction_policy
        self.protected_patterns = protected_patterns or []

        # LFU tracking (in-memory, synced to Redis)
        self._access_counts: Dict[str, int] = defaultdict(int)
        self._last_access: Dict[str, datetime] = {}
        self._protected_keys: Set[str] = set()

        # Eviction statistics
        self._eviction_count = 0
        self._eviction_log: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize Redis connection pool"""
        if self._initialized:
            logger.warning("L1 cache already initialized")
            return

        try:
            # Configure Redis eviction policy
            maxmemory_policy = self._get_redis_eviction_policy()

            self._redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                max_connections=settings.redis_max_connections,
                socket_timeout=settings.redis_socket_timeout,
            )

            # Test connection
            ping_result = await self._redis.ping()  # type: ignore[misc]
            if not ping_result:
                raise CacheError("Redis ping failed")

            # Configure Redis eviction policy
            await self._redis.config_set("maxmemory-policy", maxmemory_policy)

            self._initialized = True
            logger.info(
                "L1 cache initialized",
                host=settings.redis_host,
                port=settings.redis_port,
                eviction_policy=self.eviction_policy.value,
                redis_policy=maxmemory_policy
            )

        except Exception as e:
            logger.error(f"Failed to initialize L1 cache: {e}")
            raise CacheError(f"L1 cache initialization failed: {e}")

    async def shutdown(self) -> None:
        """Close Redis connections"""
        if self._redis:
            await self._redis.aclose()
            self._initialized = False
            logger.info("L1 cache shutdown")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        try:
            value = await self._redis.get(key)
            if value:
                # Track access for LFU
                self._track_access(key)

                logger.debug("L1 cache hit", key=key)
                result: Any = json.loads(value)
                return result
            else:
                logger.debug("L1 cache miss", key=key)
                return None

        except Exception as e:
            logger.error(f"L1 cache get error: {e}", key=key)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with optional TTL

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        try:
            serialized = json.dumps(value, default=str)

            if ttl_seconds:
                await self._redis.setex(key, ttl_seconds, serialized)
            else:
                await self._redis.set(key, serialized)

            logger.debug("L1 cache set", key=key, ttl=ttl_seconds)
            return True

        except Exception as e:
            logger.error(f"L1 cache set error: {e}", key=key)
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        try:
            result = await self._redis.delete(key)
            logger.debug("L1 cache delete", key=key, deleted=bool(result))
            return bool(result)

        except Exception as e:
            logger.error(f"L1 cache delete error: {e}", key=key)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            logger.error(f"L1 cache exists error: {e}", key=key)
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key in seconds"""
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        try:
            ttl = await self._redis.ttl(key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"L1 cache get_ttl error: {e}", key=key)
            return None

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Redis pattern (e.g., "price:*")

        Returns:
            Number of keys deleted
        """
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info("L1 cache cleared pattern", pattern=pattern, count=deleted)
                return int(deleted) if deleted else 0
            return 0

        except Exception as e:
            logger.error(f"L1 cache clear_pattern error: {e}", pattern=pattern)
            return 0

    async def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        try:
            info = await self._redis.info("stats")
            return {
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                ),
            }
        except Exception as e:
            logger.error(f"L1 cache get_stats error: {e}")
            return {}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

    def build_key(self, *parts: str) -> str:
        """Build cache key from parts"""
        return ":".join(str(part) for part in parts)

    async def get_many(self, keys: List[str]) -> List[Optional[Any]]:
        """
        Get multiple values from cache in a single operation (pipeline optimization)

        Args:
            keys: List of cache keys

        Returns:
            List of cached values (None for missing keys)
        """
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        if not keys:
            return []

        try:
            # Use pipeline for batch get operations
            async with self._redis.pipeline() as pipe:
                for key in keys:
                    pipe.get(key)
                values = await pipe.execute()

            results = []
            for key, value in zip(keys, values, strict=False):
                if value:
                    try:
                        results.append(json.loads(value))
                        logger.debug("L1 cache hit", key=key)
                    except Exception as e:
                        logger.error(f"L1 cache parse error: {e}", key=key)
                        results.append(None)
                else:
                    logger.debug("L1 cache miss", key=key)
                    results.append(None)

            return results

        except Exception as e:
            logger.error(f"L1 cache get_many error: {e}")
            return [None] * len(keys)

    async def set_many(self, items: List[tuple[str, Any, Optional[int]]]) -> int:
        """
        Set multiple values in cache in a single operation (pipeline optimization)

        Args:
            items: List of (key, value, ttl_seconds) tuples

        Returns:
            Number of successfully set items
        """
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        if not items:
            return 0

        try:
            # Use pipeline for batch set operations
            async with self._redis.pipeline() as pipe:
                for key, value, ttl_seconds in items:
                    try:
                        serialized = json.dumps(value, default=str)
                        if ttl_seconds:
                            pipe.setex(key, ttl_seconds, serialized)
                        else:
                            pipe.set(key, serialized)
                    except Exception as e:
                        logger.error(f"L1 cache serialization error: {e}", key=key)

                results = await pipe.execute()

            success_count = sum(1 for r in results if r)
            logger.debug("L1 cache set_many", total=len(items), success=success_count)
            return success_count

        except Exception as e:
            logger.error(f"L1 cache set_many error: {e}")
            return 0


    def _get_redis_eviction_policy(self) -> str:
        """Map our eviction policy to Redis config"""
        if self.eviction_policy == EvictionPolicy.LRU:
            return "allkeys-lru"
        elif self.eviction_policy == EvictionPolicy.LFU:
            return "allkeys-lfu"
        else:  # HYBRID
            return "volatile-lfu"  # LFU for keys with TTL

    def _track_access(self, key: str) -> None:
        """Track key access for LFU policy"""
        self._access_counts[key] += 1
        self._last_access[key] = datetime.utcnow()

    def protect_key(self, key: str) -> None:
        """
        Protect a key from eviction

        Args:
            key: Key to protect
        """
        self._protected_keys.add(key)
        logger.debug("Key protected from eviction", key=key)

    def unprotect_key(self, key: str) -> None:
        """
        Remove protection from a key

        Args:
            key: Key to unprotect
        """
        self._protected_keys.discard(key)
        logger.debug("Key unprotected", key=key)

    def is_protected(self, key: str) -> bool:
        """Check if key is protected"""
        # Check exact match
        if key in self._protected_keys:
            return True

        # Check pattern matches
        return any(self._matches_pattern(key, pattern) for pattern in self.protected_patterns)

    @staticmethod
    def _matches_pattern(key: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)"""
        if "*" not in pattern:
            return key == pattern

        # Convert pattern to regex-like matching
        parts = pattern.split("*")
        if len(parts) == 2:
            prefix, suffix = parts
            return key.startswith(prefix) and key.endswith(suffix)

        return False

    async def evict_least_used(self, count: int = 10) -> int:
        """
        Manually evict least used keys (for LFU/HYBRID policies)

        Args:
            count: Number of keys to evict

        Returns:
            Number of keys actually evicted
        """
        if not self._initialized or self._redis is None:
            raise CacheError("L1 cache not initialized")

        # Sort keys by access count (ascending)
        sorted_keys = sorted(
            self._access_counts.items(),
            key=lambda x: x[1]
        )

        evicted = 0
        for key, access_count in sorted_keys[:count]:
            # Skip protected keys
            if self.is_protected(key):
                logger.debug("Skipping eviction of protected key", key=key)
                continue

            # Check if key still exists
            if await self.exists(key):
                success = await self.delete(key)
                if success:
                    evicted += 1
                    self._log_eviction(key, access_count, "manual_lfu")

            # Clean up tracking data
            if key in self._access_counts:
                del self._access_counts[key]
            if key in self._last_access:
                del self._last_access[key]

        logger.info("Manual eviction complete", target=count, evicted=evicted)
        return evicted

    def _log_eviction(self, key: str, access_count: int, reason: str) -> None:
        """Log eviction decision for analysis"""
        self._eviction_count += 1

        eviction_record = {
            "key": key,
            "access_count": access_count,
            "last_access": self._last_access.get(key),
            "reason": reason,
            "timestamp": datetime.utcnow(),
        }

        self._eviction_log.append(eviction_record)

        # Keep only last 1000 evictions
        if len(self._eviction_log) > 1000:
            self._eviction_log.pop(0)

        logger.info(
            "Cache key evicted",
            key=key,
            access_count=access_count,
            reason=reason
        )

    def get_eviction_stats(self) -> Dict[str, Any]:
        """Get eviction statistics"""
        return {
            "total_evictions": self._eviction_count,
            "recent_evictions": len(self._eviction_log),
            "protected_keys": len(self._protected_keys),
            "tracked_keys": len(self._access_counts),
            "eviction_policy": self.eviction_policy.value,
        }

    def get_access_stats(self) -> Dict[str, Any]:
        """Get access frequency statistics"""
        if not self._access_counts:
            return {
                "total_tracked": 0,
                "most_accessed": [],
                "least_accessed": [],
            }

        sorted_by_access = sorted(
            self._access_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "total_tracked": len(self._access_counts),
            "most_accessed": sorted_by_access[:10],
            "least_accessed": sorted_by_access[-10:],
        }


# Global L1 cache instance
l1_cache = L1Cache()
