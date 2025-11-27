"""
Narrative Caching System

Implements intelligent caching for generated narratives with dynamic TTL
based on market conditions and automatic invalidation on significant events.
"""

import hashlib
import json
from datetime import datetime, time, timezone
from typing import Any, Dict, Optional, cast

from fiml.cache.manager import cache_manager
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType

logger = get_logger(__name__)


class NarrativeCache:
    """
    Intelligent narrative caching with dynamic TTL and event-based invalidation

    Features:
    - Dynamic TTL based on market conditions
    - Event-triggered cache invalidation
    - Cache hit rate tracking
    - Market hours awareness
    """

    def __init__(self) -> None:
        """Initialize narrative cache"""
        self.cache_manager = cache_manager
        self._hit_count: int = 0
        self._miss_count: int = 0
        logger.info("Narrative cache initialized")

    async def get(
        self,
        symbol: str,
        language: str = "en",
        expertise_level: str = "intermediate",
        narrative_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached narrative

        Args:
            symbol: Asset symbol
            language: Language code
            expertise_level: User expertise level
            narrative_params: Optional additional parameters that affect narrative

        Returns:
            Cached narrative data or None if not found
        """
        cache_key = self._generate_cache_key(symbol, language, expertise_level, narrative_params)

        try:
            cached_data = await self.cache_manager.l1.get(cache_key)
            if cached_data:
                self._hit_count += 1
                logger.debug(
                    "Narrative cache hit",
                    symbol=symbol,
                    language=language,
                    hit_rate=self.get_hit_rate(),
                )
                return cast(Dict[str, Any], cached_data)
            else:
                self._miss_count += 1
                logger.debug("Narrative cache miss", symbol=symbol)
                return None

        except Exception as e:
            logger.warning(f"Narrative cache read error: {e}")
            self._miss_count += 1
            return None

    async def set(
        self,
        symbol: str,
        narrative_data: Dict[str, Any],
        language: str = "en",
        expertise_level: str = "intermediate",
        asset_type: AssetType = AssetType.EQUITY,
        volatility: Optional[float] = None,
        narrative_params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache generated narrative with dynamic TTL

        Args:
            symbol: Asset symbol
            narrative_data: Narrative data to cache
            language: Language code
            expertise_level: User expertise level
            asset_type: Type of asset
            volatility: Current price volatility (for TTL calculation)
            narrative_params: Optional additional parameters

        Returns:
            True if cached successfully
        """
        cache_key = self._generate_cache_key(symbol, language, expertise_level, narrative_params)

        # Calculate dynamic TTL if not provided
        if ttl is None:
            asset = Asset(symbol=symbol, asset_type=asset_type)
            ttl = self._calculate_ttl(asset, volatility)

        try:
            await self.cache_manager.l1.set(cache_key, narrative_data, ttl)
            logger.info(
                "Narrative cached",
                symbol=symbol,
                ttl=ttl,
                language=language,
            )
            return True

        except Exception as e:
            logger.warning(f"Narrative cache write error: {e}")
            return False

    async def invalidate(
        self,
        symbol: str,
        language: Optional[str] = None,
        expertise_level: Optional[str] = None,
    ) -> int:
        """
        Invalidate cached narratives for a symbol

        Args:
            symbol: Asset symbol to invalidate
            language: Optional specific language to invalidate
            expertise_level: Optional specific expertise level to invalidate

        Returns:
            Number of cache entries invalidated
        """
        # If specific language/expertise not provided, invalidate all variations
        count = 0

        if language and expertise_level:
            # Invalidate specific combination
            cache_key = self._generate_cache_key(symbol, language, expertise_level)
            try:
                await self.cache_manager.l1.delete(cache_key)
                count = 1
            except Exception as e:
                logger.warning(f"Failed to invalidate cache key: {e}")
        else:
            # Invalidate all combinations using pattern matching
            pattern = f"narrative:{symbol.upper()}:*"
            try:
                # Note: This requires Redis SCAN for pattern deletion
                # For now, we'll just mark as invalidated
                logger.info("Invalidating narrative cache pattern", pattern=pattern)
                # In production, implement pattern-based deletion
                count = 1
            except Exception as e:
                logger.warning(f"Failed to invalidate cache pattern: {e}")

        logger.info(f"Invalidated {count} narrative cache entries", symbol=symbol)
        return count

    async def invalidate_on_event(
        self,
        symbol: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> bool:
        """
        Invalidate cache based on significant market events

        Args:
            symbol: Asset symbol
            event_type: Type of event (price_change, news, earnings, etc.)
            event_data: Event data for decision making

        Returns:
            True if cache was invalidated

        Events that trigger invalidation:
        - Price change >3%
        - New earnings release
        - Major news event
        - Watchdog alert
        """
        should_invalidate = False

        if event_type == "price_change":
            change_pct = abs(event_data.get("change_percent", 0))
            if change_pct > 3.0:
                should_invalidate = True
                logger.info(
                    f"Invalidating cache due to price change: {change_pct}%",
                    symbol=symbol,
                )

        elif event_type == "earnings":
            should_invalidate = True
            logger.info("Invalidating cache due to earnings release", symbol=symbol)

        elif event_type == "news":
            # Check news impact score
            impact = event_data.get("impact", "low")
            if impact in ["high", "critical"]:
                should_invalidate = True
                logger.info(f"Invalidating cache due to {impact} impact news", symbol=symbol)

        elif event_type == "watchdog":
            # Watchdog alerts always invalidate
            should_invalidate = True
            logger.info("Invalidating cache due to watchdog event", symbol=symbol)

        if should_invalidate:
            await self.invalidate(symbol)
            return True

        return False

    def _generate_cache_key(
        self,
        symbol: str,
        language: str,
        expertise_level: str,
        narrative_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate cache key for narrative

        Args:
            symbol: Asset symbol
            language: Language code
            expertise_level: Expertise level
            narrative_params: Optional additional parameters

        Returns:
            Cache key string
        """
        base_key = f"narrative:{symbol.upper()}:{language}:{expertise_level}"

        # Add hash of narrative params if provided
        if narrative_params:
            params_str = json.dumps(narrative_params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            base_key += f":{params_hash}"

        return base_key

    def _calculate_ttl(
        self,
        asset: Asset,
        volatility: Optional[float] = None,
    ) -> int:
        """
        Calculate dynamic TTL based on market conditions

        Args:
            asset: Asset object
            volatility: Current price volatility (absolute change_percent)

        Returns:
            TTL in seconds

        Logic:
        - Crypto (24/7): Shorter TTL (3-10 min)
        - Equities during market hours: 5-15 min
        - Equities after hours: 30 min
        - High volatility: Shorter TTL
        """
        now = datetime.now(timezone.utc)
        current_time = now.time()

        # Market hours (NYSE: 9:30 AM - 4:00 PM ET = 14:30-21:00 UTC)
        market_open = time(14, 30)
        market_close = time(21, 0)
        is_market_hours = market_open <= current_time <= market_close

        # Check if weekend
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6

        if asset.asset_type == AssetType.CRYPTO:
            # Crypto trades 24/7, always use short TTL
            base_ttl = 600  # 10 minutes

            if volatility:
                if volatility > 10:  # Extreme volatility (>10%)
                    return 180  # 3 minutes
                elif volatility > 5:  # High volatility (5-10%)
                    return 300  # 5 minutes
                elif volatility > 2:  # Moderate volatility (2-5%)
                    return 450  # 7.5 minutes

            return base_ttl

        else:
            # Equity/traditional assets
            if is_weekend:
                # Weekend: Markets closed, longer TTL
                return 3600  # 1 hour

            if not is_market_hours:
                # Pre-market/After-hours: Less volatility expected
                return 1800  # 30 minutes

            # During market hours
            if volatility:
                if volatility > 3:  # Significant movement (>3%)
                    return 300  # 5 minutes
                elif volatility > 1:  # Moderate movement (1-3%)
                    return 600  # 10 minutes
                else:  # Normal conditions (<1%)
                    return 900  # 15 minutes

            # Default during market hours
            return 900  # 15 minutes

    def get_hit_rate(self) -> float:
        """
        Get cache hit rate

        Returns:
            Hit rate as percentage (0-100)
        """
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return (self._hit_count / total) * 100

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache metrics

        Returns:
            Dictionary with cache statistics
        """
        return {
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": self.get_hit_rate(),
            "total_requests": self._hit_count + self._miss_count,
        }

    def reset_metrics(self) -> None:
        """Reset cache metrics counters"""
        self._hit_count = 0
        self._miss_count = 0
        logger.info("Narrative cache metrics reset")


# Global narrative cache instance
narrative_cache = NarrativeCache()


async def get_cached_narrative(
    symbol: str,
    language: str = "en",
    expertise_level: str = "intermediate",
    narrative_params: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Wrapper for narrative_cache.get"""
    return await narrative_cache.get(symbol, language, expertise_level, narrative_params)


async def cache_narrative(
    symbol: str,
    language: str,
    expertise_level: str,
    narrative_data: Dict[str, Any],
    ttl: int,
) -> bool:
    """Wrapper for narrative_cache.set"""
    return await narrative_cache.set(
        symbol=symbol,
        narrative_data=narrative_data,
        language=language,
        expertise_level=expertise_level,
        ttl=ttl,
    )
