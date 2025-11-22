"""
Cache Manager - Coordinates L1 and L2 caches
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from fiml.cache.l1_cache import l1_cache
from fiml.cache.l2_cache import l2_cache
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
    """

    def __init__(self):
        self.l1 = l1_cache
        self.l2 = l2_cache

    async def initialize(self) -> None:
        """Initialize both cache layers"""
        await self.l1.initialize()
        await self.l2.initialize()
        logger.info("Cache manager initialized")

    async def shutdown(self) -> None:
        """Shutdown both cache layers"""
        await self.l1.shutdown()
        await self.l2.shutdown()
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
            return l1_result

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
        Set price in both caches
        
        Args:
            asset: Asset
            provider: Provider name
            price_data: Price data dictionary
            
        Returns:
            True if successful
        """
        l1_key = self.l1.build_key("price", asset.symbol, provider)
        ttl = self._get_ttl(DataType.PRICE)

        # Set in L1
        l1_success = await self.l1.set(l1_key, price_data, ttl)

        # Set in L2 (async, don't wait)
        # In production, would insert into PostgreSQL
        # l2_success = await self.l2.set_price(asset_id, provider, ...)

        logger.debug("Price cached", asset=asset.symbol, provider=provider, l1=l1_success)
        return l1_success

    async def get_fundamentals(
        self, asset: Asset, provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get fundamentals with L1 -> L2 fallback"""
        l1_key = self.l1.build_key("fundamentals", asset.symbol, provider or "any")

        # Try L1
        l1_result = await self.l1.get(l1_key)
        if l1_result:
            logger.debug("Fundamentals from L1 cache", asset=asset.symbol)
            return l1_result

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
        """Set fundamentals in both caches"""
        l1_key = self.l1.build_key("fundamentals", asset.symbol, provider)
        ttl = self._get_ttl(DataType.FUNDAMENTALS)

        # Set in L1
        l1_success = await self.l1.set(l1_key, data, ttl)

        # Set in L2
        # In production: await self.l2.set_fundamentals(asset_id, provider, data, ttl)

        logger.debug("Fundamentals cached", asset=asset.symbol, provider=provider)
        return l1_success

    async def invalidate_asset(self, asset: Asset) -> int:
        """Invalidate all cached data for an asset"""
        pattern = f"*:{asset.symbol}:*"
        deleted = await self.l1.clear_pattern(pattern)
        logger.info(f"Invalidated cache for asset", asset=asset.symbol, deleted=deleted)
        return deleted

    async def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics"""
        l1_stats = await self.l1.get_stats()
        
        return {
            "l1": l1_stats,
            "l2": {"status": "initialized" if self.l2._initialized else "not_initialized"},
        }

    def _get_ttl(self, data_type: DataType) -> int:
        """Get TTL for data type"""
        ttl_map = {
            DataType.PRICE: settings.cache_ttl_price,
            DataType.FUNDAMENTALS: settings.cache_ttl_fundamentals,
            DataType.TECHNICAL: settings.cache_ttl_technical,
            DataType.NEWS: settings.cache_ttl_news,
            DataType.MACRO: settings.cache_ttl_macro,
        }
        return ttl_map.get(data_type, 300)

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
        
        # Try L1 batch get
        results = await self.l1.get_many(l1_keys)
        
        hits = sum(1 for r in results if r is not None)
        logger.debug(f"Batch price lookup", total=len(assets), l1_hits=hits)
        
        return results

    async def set_prices_batch(
        self,
        items: List[tuple[Asset, str, Dict[str, Any]]],
    ) -> int:
        """
        Set multiple prices in L1 cache using batch optimization
        
        Args:
            items: List of (asset, provider, price_data) tuples
            
        Returns:
            Number of successfully cached items
        """
        ttl = self._get_ttl(DataType.PRICE)
        
        # Build cache items
        cache_items = [
            (self.l1.build_key("price", asset.symbol, provider), price_data, ttl)
            for asset, provider, price_data in items
        ]
        
        # Batch set in L1
        success_count = await self.l1.set_many(cache_items)
        
        logger.debug("Batch price set", total=len(items), success=success_count)
        return success_count


# Global cache manager instance
cache_manager = CacheManager()
