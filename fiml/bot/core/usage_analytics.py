"""
Provider API Usage Analytics and Quota Management

Tracks API usage per provider with Redis persistence, quota warnings,
and comprehensive usage statistics.
"""

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Dict, Optional, cast

from fiml.core.logging import get_logger

logger = get_logger(__name__)

# Provider quota limits (free tier)
PROVIDER_LIMITS = {
    "alphavantage": {"daily": 500, "monthly": 25000, "tier": "free"},
    "fmp": {"daily": 250, "monthly": 7500, "tier": "free"},
    "finnhub": {"daily": 60, "monthly": 1800, "tier": "free"},  # 60 calls/day
    "polygon": {"daily": 5, "monthly": 150, "tier": "free"},  # 5 calls/min
    "binance": {"daily": 1200, "monthly": 36000, "tier": "free"},  # Weight-based
    "coinbase": {"daily": 10000, "monthly": 300000, "tier": "free"},
    "yfinance": {"daily": float('inf'), "monthly": float('inf'), "tier": "free"},  # Unlimited
}

# Quota warning threshold
QUOTA_WARNING_THRESHOLD = 0.8  # 80%


class UsageAnalytics:
    """
    Provider API usage tracking and quota management

    Features:
    - Redis-based persistent counters
    - Daily/monthly aggregation
    - Quota threshold warnings (80%)
    - Per-provider limits

    Redis Key Pattern:
        usage:{user_id}:{provider}:{period}

    Examples:
        usage:user123:binance:2025-11-28 (daily)
        usage:user123:binance:2025-11 (monthly)
    """

    def __init__(self, redis_client: Optional[Any] = None) -> None:
        """
        Initialize usage analytics

        Args:
            redis_client: Optional Redis client (if None, uses in-memory fallback)
        """
        self._redis = redis_client
        self._in_memory_fallback: Dict[str, int] = defaultdict(int)

        logger.info(
            "UsageAnalytics initialized",
            redis_enabled=redis_client is not None
        )

    def _get_redis_key(self, user_id: str, provider: str, period_type: str = "daily") -> str:
        """
        Generate Redis key for usage tracking

        Args:
            user_id: User identifier
            provider: Provider name
            period_type: "daily" or "monthly"

        Returns:
            Redis key string
        """
        now = datetime.now(UTC)

        if period_type == "daily":
            period = now.strftime("%Y-%m-%d")
        elif period_type == "monthly":
            period = now.strftime("%Y-%m")
        else:
            raise ValueError(f"Invalid period_type: {period_type}")

        return f"usage:{user_id}:{provider}:{period}"

    async def track_call(
        self,
        user_id: str,
        provider: str,
        operation: str = "api_call"
    ) -> Dict[str, Any]:
        """
        Track an API call for a provider

        Args:
            user_id: User identifier
            provider: Provider name
            operation: Operation type (for future granularity)

        Returns:
            Dict with tracking confirmation
        """
        try:
            daily_key = self._get_redis_key(user_id, provider, "daily")
            monthly_key = self._get_redis_key(user_id, provider, "monthly")

            if self._redis:
                # Use pipeline for atomic increment and expiry
                async with self._redis.pipeline() as pipe:
                    await pipe.incr(daily_key)
                    await pipe.expire(daily_key, 86400 * 30)  # 30 days
                    await pipe.incr(monthly_key)
                    await pipe.expire(monthly_key, 86400 * 90)  # 90 days
                    await pipe.execute()

                daily_count = int(await self._redis.get(daily_key) or 0)
                monthly_count = int(await self._redis.get(monthly_key) or 0)
            else:
                # In-memory fallback
                self._in_memory_fallback[daily_key] += 1
                self._in_memory_fallback[monthly_key] += 1

                daily_count = self._in_memory_fallback[daily_key]
                monthly_count = self._in_memory_fallback[monthly_key]

            logger.debug(
                "API call tracked",
                user_id=user_id,
                provider=provider,
                daily_count=daily_count,
                monthly_count=monthly_count
            )

            return {
                "tracked": True,
                "daily_count": daily_count,
                "monthly_count": monthly_count,
            }

        except Exception as e:
            logger.error(
                "Failed to track API call",
                user_id=user_id,
                provider=provider,
                error=str(e)
            )
            return {"tracked": False, "error": str(e)}

    async def get_usage(
        self,
        user_id: str,
        provider: str,
        period_type: str = "daily"
    ) -> int:
        """
        Get usage count for a provider

        Args:
            user_id: User identifier
            provider: Provider name
            period_type: "daily" or "monthly"

        Returns:
            Usage count
        """
        try:
            key = self._get_redis_key(user_id, provider, period_type)

            if self._redis:
                count = await self._redis.get(key)
                return int(count) if count else 0
            else:
                return self._in_memory_fallback.get(key, 0)

        except Exception as e:
            logger.error(
                "Failed to get usage",
                user_id=user_id,
                provider=provider,
                period_type=period_type,
                error=str(e)
            )
            return 0

    async def get_all_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for all providers

        Args:
            user_id: User identifier

        Returns:
            Dict with comprehensive usage stats
        """
        stats = []
        total_calls_today = 0
        has_warnings = False

        for provider in PROVIDER_LIMITS.keys():
            daily_usage = await self.get_usage(user_id, provider, "daily")
            monthly_usage = await self.get_usage(user_id, provider, "monthly")

            # Skip providers with zero usage
            if daily_usage == 0 and monthly_usage == 0:
                continue

            limits = PROVIDER_LIMITS[provider]
            daily_limit = cast(float, limits["daily"])
            monthly_limit = cast(float, limits["monthly"])

            # Calculate percentages
            daily_percentage = (daily_usage / daily_limit * 100) if daily_limit != float('inf') else 0
            monthly_percentage = (monthly_usage / monthly_limit * 100) if monthly_limit != float('inf') else 0

            # Check for warnings (>= 80% threshold)
            warning = daily_percentage >= (QUOTA_WARNING_THRESHOLD * 100) or \
                     monthly_percentage >= (QUOTA_WARNING_THRESHOLD * 100)

            if warning:
                has_warnings = True

            total_calls_today += daily_usage

            stats.append({
                "provider": provider,
                "daily_usage": daily_usage,
                "daily_limit": daily_limit,
                "monthly_usage": monthly_usage,
                "monthly_limit": monthly_limit,
                "daily_percentage": round(daily_percentage, 2),
                "monthly_percentage": round(monthly_percentage, 2),
                "warning": warning,
                "tier": limits["tier"],
            })

        # Sort by daily usage (descending)
        stats.sort(key=lambda x: cast(int, x["daily_usage"]), reverse=True)

        return {
            "stats": stats,
            "total_calls_today": total_calls_today,
            "has_warnings": has_warnings,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def check_quota(
        self,
        user_id: str,
        provider: str
    ) -> Dict[str, Any]:
        """
        Check if user is approaching or exceeded quota

        Args:
            user_id: User identifier
            provider: Provider name

        Returns:
            Dict with quota status and warning
        """
        daily_usage = await self.get_usage(user_id, provider, "daily")
        monthly_usage = await self.get_usage(user_id, provider, "monthly")

        limits = self.get_provider_limits(provider)
        daily_limit = limits["daily"]
        monthly_limit = limits["monthly"]

        # Calculate percentages
        daily_percentage = (daily_usage / daily_limit * 100) if daily_limit != float('inf') else 0
        monthly_percentage = (monthly_usage / monthly_limit * 100) if monthly_limit != float('inf') else 0

        # Determine warning status
        warning = daily_percentage >= (QUOTA_WARNING_THRESHOLD * 100) or \
                 monthly_percentage >= (QUOTA_WARNING_THRESHOLD * 100)

        exceeded = daily_usage >= daily_limit or monthly_usage >= monthly_limit

        if exceeded:
            logger.warning(
                "Quota exceeded",
                user_id=user_id,
                provider=provider,
                daily_usage=daily_usage,
                daily_limit=daily_limit
            )
        elif warning:
            logger.info(
                "Approaching quota limit",
                user_id=user_id,
                provider=provider,
                daily_percentage=daily_percentage
            )

        return {
            "provider": provider,
            "warning": warning,
            "exceeded": exceeded,
            "daily_usage": daily_usage,
            "daily_limit": daily_limit,
            "monthly_usage": monthly_usage,
            "monthly_limit": monthly_limit,
            "daily_percentage": round(daily_percentage, 2),
            "monthly_percentage": round(monthly_percentage, 2),
        }

    def get_provider_limits(self, provider: str) -> Dict[str, Any]:
        """
        Get quota limits for a provider

        Args:
            provider: Provider name

        Returns:
            Dict with daily/monthly limits
        """
        return PROVIDER_LIMITS.get(provider, {
            "daily": 1000,
            "monthly": 30000,
            "tier": "unknown"
        })

    async def reset_usage(
        self,
        user_id: str,
        provider: Optional[str] = None,
        period_type: str = "daily"
    ) -> Dict[str, Any]:
        """
        Reset usage counters (for testing/admin)

        Args:
            user_id: User identifier
            provider: Provider name (if None, resets all)
            period_type: "daily" or "monthly"

        Returns:
            Dict with reset confirmation
        """
        try:
            if provider:
                providers = [provider]
            else:
                providers = list(PROVIDER_LIMITS.keys())

            reset_count = 0
            for prov in providers:
                key = self._get_redis_key(user_id, prov, period_type)

                if self._redis:
                    await self._redis.delete(key)
                else:
                    if key in self._in_memory_fallback:
                        del self._in_memory_fallback[key]

                reset_count += 1

            logger.info(
                "Usage counters reset",
                user_id=user_id,
                provider=provider or "all",
                period_type=period_type,
                reset_count=reset_count
            )

            return {
                "reset": True,
                "providers_reset": reset_count,
            }

        except Exception as e:
            logger.error(
                "Failed to reset usage",
                user_id=user_id,
                provider=provider,
                error=str(e)
            )
            return {"reset": False, "error": str(e)}
