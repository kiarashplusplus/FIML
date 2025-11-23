"""
L1 Cache - Redis In-Memory Cache
Target: 10-100ms latency
"""

import json
from typing import Any, List, Optional

import redis.asyncio as redis

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
    """

    def __init__(self) -> None:
        self._redis: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection pool"""
        if self._initialized:
            logger.warning("L1 cache already initialized")
            return

        try:
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

            self._initialized = True
            logger.info("L1 cache initialized", host=settings.redis_host, port=settings.redis_port)

        except Exception as e:
            logger.error(f"Failed to initialize L1 cache: {e}")
            raise CacheError(f"L1 cache initialization failed: {e}")

    async def shutdown(self) -> None:
        """Close Redis connections"""
        if self._redis:
            await self._redis.close()
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


# Global L1 cache instance
l1_cache = L1Cache()
