"""
L2 Cache - PostgreSQL + TimescaleDB Persistent Cache
Target: 300-700ms latency
"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fiml.core import config
from fiml.core.exceptions import CacheError
from fiml.core.logging import get_logger

logger = get_logger(__name__)


class L2Cache:
    """
    PostgreSQL + TimescaleDB L2 cache for persistent data

    Features:
    - 300-700ms latency target
    - Time-series optimized with TimescaleDB
    - Automatic data retention policies
    - Historical data queries
    """

    def __init__(self) -> None:
        self._engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize PostgreSQL connection pool"""
        if self._initialized:
            logger.warning("L2 cache already initialized")
            return

        try:
            # Create async engine
            self._engine = create_async_engine(
                config.settings.database_url,
                pool_size=config.settings.postgres_pool_size,
                max_overflow=config.settings.postgres_max_overflow,
                echo=config.settings.is_development,
            )

            # Create session maker
            self._session_maker = async_sessionmaker(
                self._engine,
                expire_on_commit=False,
            )

            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            self._initialized = True
            logger.info("L2 cache initialized", url=config.settings.database_url.split("@")[-1])

        except Exception as e:
            logger.error(f"Failed to initialize L2 cache: {e}")
            raise CacheError(f"L2 cache initialization failed: {e}")

    async def shutdown(self) -> None:
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()
            self._initialized = False
            logger.info("L2 cache shutdown")

    async def get_price(
        self,
        asset_id: int,
        provider: Optional[str] = None,
        time_range_minutes: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Get recent price from cache

        Args:
            asset_id: Asset ID
            provider: Specific provider (optional)
            time_range_minutes: How far back to look

        Returns:
            Price data or None
        """
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    SELECT time, asset_id, provider, price, change, change_percent,
                           volume, confidence, metadata
                    FROM price_cache
                    WHERE asset_id = :asset_id
                        AND time >= NOW() - INTERVAL ':minutes minutes'
                        AND (:provider IS NULL OR provider = :provider)
                    ORDER BY time DESC
                    LIMIT 1
                """
                )

                result = await session.execute(
                    query,
                    {
                        "asset_id": asset_id,
                        "minutes": time_range_minutes,
                        "provider": provider,
                    },
                )

                row = result.fetchone()
                if row:
                    return {
                        "time": row[0],
                        "asset_id": row[1],
                        "provider": row[2],
                        "price": row[3],
                        "change": row[4],
                        "change_percent": row[5],
                        "volume": row[6],
                        "confidence": row[7],
                        "metadata": row[8],
                    }
                return None

        except Exception as e:
            logger.error(f"L2 cache get_price error: {e}", asset_id=asset_id)
            return None

    async def set_price(
        self,
        asset_id: int,
        provider: str,
        price: float,
        change: Optional[float] = None,
        change_percent: Optional[float] = None,
        volume: Optional[int] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Insert price data into cache"""
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    INSERT INTO price_cache
                    (time, asset_id, provider, price, change, change_percent,
                     volume, confidence, metadata)
                    VALUES (NOW(), :asset_id, :provider, :price, :change,
                            :change_percent, :volume, :confidence, :metadata)
                """
                )

                await session.execute(
                    query,
                    {
                        "asset_id": asset_id,
                        "provider": provider,
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "volume": volume,
                        "confidence": confidence,
                        "metadata": metadata,
                    },
                )

                await session.commit()
                logger.debug("L2 cache price set", asset_id=asset_id, provider=provider)
                return True

        except Exception as e:
            logger.error(f"L2 cache set_price error: {e}", asset_id=asset_id)
            return False

    async def get_ohlcv(
        self,
        asset_id: int,
        timeframe: str = "1d",
        limit: int = 100,
        provider: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get OHLCV data from cache"""
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    SELECT time, asset_id, provider, open, high, low, close,
                           volume, timeframe
                    FROM ohlcv_cache
                    WHERE asset_id = :asset_id
                        AND timeframe = :timeframe
                        AND (:provider IS NULL OR provider = :provider)
                    ORDER BY time DESC
                    LIMIT :limit
                """
                )

                result = await session.execute(
                    query,
                    {
                        "asset_id": asset_id,
                        "timeframe": timeframe,
                        "provider": provider,
                        "limit": limit,
                    },
                )

                rows = result.fetchall()
                return [
                    {
                        "time": row[0],
                        "asset_id": row[1],
                        "provider": row[2],
                        "open": row[3],
                        "high": row[4],
                        "low": row[5],
                        "close": row[6],
                        "volume": row[7],
                        "timeframe": row[8],
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"L2 cache get_ohlcv error: {e}", asset_id=asset_id)
            return []

    async def get_fundamentals(
        self, asset_id: int, provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get fundamentals from cache"""
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    SELECT id, asset_id, provider, data, timestamp, ttl_seconds
                    FROM fundamentals_cache
                    WHERE asset_id = :asset_id
                        AND (:provider IS NULL OR provider = :provider)
                        AND timestamp >= NOW() - INTERVAL '1 second' * ttl_seconds
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                )

                result = await session.execute(query, {"asset_id": asset_id, "provider": provider})

                row = result.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "asset_id": row[1],
                        "provider": row[2],
                        "data": row[3],
                        "timestamp": row[4],
                        "ttl_seconds": row[5],
                    }
                return None

        except Exception as e:
            logger.error(f"L2 cache get_fundamentals error: {e}", asset_id=asset_id)
            return None

    async def set_fundamentals(
        self,
        asset_id: int,
        provider: str,
        data: Dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> bool:
        """Insert/update fundamentals in cache"""
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                # Upsert using ON CONFLICT
                query = text(
                    """
                    INSERT INTO fundamentals_cache
                    (asset_id, provider, data, timestamp, ttl_seconds)
                    VALUES (:asset_id, :provider, :data, NOW(), :ttl_seconds)
                    ON CONFLICT (asset_id, provider)
                    DO UPDATE SET
                        data = EXCLUDED.data,
                        timestamp = EXCLUDED.timestamp,
                        ttl_seconds = EXCLUDED.ttl_seconds
                """
                )

                await session.execute(
                    query,
                    {
                        "asset_id": asset_id,
                        "provider": provider,
                        "data": data,
                        "ttl_seconds": ttl_seconds,
                    },
                )

                await session.commit()
                logger.debug("L2 cache fundamentals set", asset_id=asset_id)
                return True

        except Exception as e:
            logger.error(f"L2 cache set_fundamentals error: {e}", asset_id=asset_id)
            return False

    async def cleanup_expired(self) -> int:
        """Remove expired data (called by scheduled task)"""
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    DELETE FROM fundamentals_cache
                    WHERE timestamp < NOW() - INTERVAL '1 second' * ttl_seconds
                """
                )

                result = await session.execute(query)
                await session.commit()

                deleted = int(result.rowcount) if result.rowcount else 0  # type: ignore[attr-defined]
                logger.info("L2 cache cleanup", deleted=deleted)
                return deleted

        except Exception as e:
            logger.error(f"L2 cache cleanup error: {e}")
            return 0

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """
        Generic set method for key-value storage

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                # Use generic cache table for key-value storage
                query = text(
                    """
                    INSERT INTO generic_cache
                    (key, value, timestamp, ttl_seconds)
                    VALUES (:key, :value, NOW(), :ttl_seconds)
                    ON CONFLICT (key)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        timestamp = EXCLUDED.timestamp,
                        ttl_seconds = EXCLUDED.ttl_seconds
                """
                )

                await session.execute(
                    query,
                    {
                        "key": key,
                        "value": json.dumps(value),
                        "ttl_seconds": ttl_seconds or 3600,
                    },
                )

                await session.commit()
                logger.debug("L2 cache set", key=key)
                return True

        except Exception as e:
            logger.error(f"L2 cache set error: {e}", key=key)
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Generic get method for key-value retrieval

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    SELECT value
                    FROM generic_cache
                    WHERE key = :key
                        AND timestamp >= NOW() - INTERVAL '1 second' * ttl_seconds
                    LIMIT 1
                """
                )

                result = await session.execute(query, {"key": key})
                row = result.fetchone()

                if row:
                    # JSONB is automatically deserialized by asyncpg
                    return row[0]
                return None

        except Exception as e:
            logger.error(f"L2 cache get error: {e}", key=key)
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    DELETE FROM generic_cache
                    WHERE key = :key
                """
                )

                result = await session.execute(query, {"key": key})
                await session.commit()

                deleted = bool(result.rowcount) if result.rowcount else False  # type: ignore[attr-defined]
                logger.debug("L2 cache delete", key=key, deleted=deleted)
                return deleted

        except Exception as e:
            logger.error(f"L2 cache delete error: {e}", key=key)
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if key exists and is not expired
        """
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    SELECT 1
                    FROM generic_cache
                    WHERE key = :key
                        AND timestamp >= NOW() - INTERVAL '1 second' * ttl_seconds
                    LIMIT 1
                """
                )

                result = await session.execute(query, {"key": key})
                return result.fetchone() is not None

        except Exception as e:
            logger.error(f"L2 cache exists error: {e}", key=key)
            return False

    async def clear(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of entries deleted
        """
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text("DELETE FROM generic_cache")
                result = await session.execute(query)
                await session.commit()

                deleted = int(result.rowcount) if result.rowcount else 0  # type: ignore[attr-defined]
                logger.info("L2 cache cleared", deleted=deleted)
                return deleted

        except Exception as e:
            logger.error(f"L2 cache clear error: {e}")
            return 0

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear cache entries matching a pattern

        Args:
            pattern: SQL LIKE pattern (e.g., 'price:%')

        Returns:
            Number of entries deleted
        """
        if not self._initialized or self._session_maker is None:
            raise CacheError("L2 cache not initialized")

        try:
            async with self._session_maker() as session:
                query = text(
                    """
                    DELETE FROM generic_cache
                    WHERE key LIKE :pattern
                """
                )

                result = await session.execute(query, {"pattern": pattern})
                await session.commit()

                deleted = int(result.rowcount) if result.rowcount else 0  # type: ignore[attr-defined]
                logger.info("L2 cache pattern cleared", pattern=pattern, deleted=deleted)
                return deleted

        except Exception as e:
            logger.error(f"L2 cache clear_pattern error: {e}", pattern=pattern)
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get L2 cache statistics

        Returns:
            Statistics dictionary
        """
        if not self._initialized or self._session_maker is None:
            return {
                "status": "not_initialized",
                "entries": 0,
            }

        try:
            async with self._session_maker() as session:
                # Count total entries
                count_query = text("SELECT COUNT(*) FROM generic_cache")
                count_result = await session.execute(count_query)
                total_entries = count_result.scalar() or 0

                # Count expired entries
                expired_query = text(
                    """
                    SELECT COUNT(*)
                    FROM generic_cache
                    WHERE timestamp < NOW() - INTERVAL '1 second' * ttl_seconds
                """
                )
                expired_result = await session.execute(expired_query)
                expired_entries = expired_result.scalar() or 0

                return {
                    "status": "initialized",
                    "entries": total_entries,  # For backward compatibility
                    "total_entries": total_entries,
                    "expired_entries": expired_entries,
                    "active_entries": total_entries - expired_entries,
                }

        except Exception as e:
            logger.error(f"L2 cache get_stats error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }


# Global L2 cache instance
l2_cache = L2Cache()
