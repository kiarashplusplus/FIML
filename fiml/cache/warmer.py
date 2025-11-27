"""
Cache Warming System

Proactively loads frequently accessed data into cache layers
to improve performance and reduce cold-start latency.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fiml.cache.manager import cache_manager
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, Market

logger = get_logger(__name__)


class CacheWarmer:
    """
    Cache warming system for proactive data loading

    Features:
    - Warm popular symbols on startup
    - Scheduled warming for frequently accessed data
    - Configurable symbol lists
    - Performance metrics tracking
    """

    def __init__(self) -> None:
        self._warming_in_progress = False
        self._last_warm_time: Optional[datetime] = None
        self._warm_count = 0
        self._warm_errors = 0

    @property
    def popular_symbols(self) -> List[str]:
        """
        Get list of popular symbols to warm

        These are the most frequently accessed symbols that should
        be kept in cache for optimal performance.
        """
        return [
            # Major US Tech Stocks (FAANG+)
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "META",
            "NVDA",
            "TSLA",
            # Major Indices
            "SPY",
            "QQQ",
            "DIA",
            "IWM",
            # Popular stocks
            "AMD",
            "NFLX",
            "DIS",
            "INTC",
            "PYPL",
            "CRM",
            "ADBE",
            # Major Cryptos
            "BTC",
            "ETH",
            "BNB",
            "SOL",
            "ADA",
        ]

    def get_assets_to_warm(self) -> List[Asset]:
        """
        Convert popular symbols to Asset objects

        Returns:
            List of Asset objects for warming
        """
        assets = []

        # Crypto symbols set for fast lookup
        crypto_set = {"BTC", "ETH", "BNB", "SOL", "ADA"}

        # NASDAQ symbols
        nasdaq_symbols = {
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "META",
            "NVDA",
            "TSLA",
            "AMD",
            "NFLX",
            "INTC",
            "PYPL",
            "CRM",
            "ADBE",
        }

        # Equity assets
        equity_symbols = [s for s in self.popular_symbols if s not in crypto_set]
        for symbol in equity_symbols:
            assets.append(
                Asset(
                    symbol=symbol,
                    name=f"{symbol} Stock",
                    asset_type=AssetType.EQUITY,
                    market=Market.US,
                    exchange="NASDAQ" if symbol in nasdaq_symbols else "NYSE",
                    currency="USD",
                )
            )

        # Crypto assets
        for symbol in crypto_set:
            if symbol in self.popular_symbols:
                assets.append(
                    Asset(
                        symbol=symbol,
                        name=f"{symbol} Crypto",
                        asset_type=AssetType.CRYPTO,
                        market=Market.CRYPTO,
                        exchange="binance",
                        currency="USDT",
                    )
                )

        return assets

    async def warm_cache(
        self, assets: Optional[List[Asset]] = None, force: bool = False
    ) -> Dict[str, Any]:
        """
        Warm cache with data for specified assets

        Args:
            assets: List of assets to warm (uses popular_symbols if None)
            force: Force warming even if already in progress

        Returns:
            Warming statistics
        """
        if self._warming_in_progress and not force:
            logger.warning("Cache warming already in progress")
            return {"status": "skipped", "reason": "warming_in_progress"}

        self._warming_in_progress = True
        start_time = datetime.now(timezone.utc)

        try:
            # Use default popular symbols if none provided
            if assets is None:
                assets = self.get_assets_to_warm()

            logger.info(f"Starting cache warming for {len(assets)} assets")

            # Warm placeholder data (in production, this would fetch from providers)
            success_count = 0
            error_count = 0

            for asset in assets:
                try:
                    # Create placeholder price data
                    price_data = {
                        "symbol": asset.symbol,
                        "price": 100.0,  # Placeholder
                        "change": 0.0,
                        "change_percent": 0.0,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "warmed": True,
                    }

                    # Set in cache with standard TTL
                    success = await cache_manager.set_price(
                        asset=asset, provider="cache_warmer", price_data=price_data
                    )

                    if success:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    logger.error(f"Error warming cache for {asset.symbol}: {e}")
                    error_count += 1

            # Update statistics
            self._warm_count += success_count
            self._warm_errors += error_count
            self._last_warm_time = datetime.now(timezone.utc)

            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(
                "Cache warming completed",
                total=len(assets),
                success=success_count,
                errors=error_count,
                duration_ms=f"{duration_ms:.2f}",
            )

            return {
                "status": "completed",
                "total_assets": len(assets),
                "success_count": success_count,
                "error_count": error_count,
                "duration_ms": duration_ms,
                "timestamp": self._last_warm_time.isoformat(),
            }

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return {"status": "failed", "error": str(e)}

        finally:
            self._warming_in_progress = False

    async def warm_on_startup(self) -> Dict[str, Any]:
        """
        Warm cache on application startup

        This should be called during application initialization
        to pre-populate cache with frequently accessed data.

        Returns:
            Warming statistics
        """
        logger.info("Performing startup cache warming")
        return await self.warm_cache()

    async def scheduled_warm(self, interval_seconds: int = 300) -> None:
        """
        Run scheduled cache warming

        Args:
            interval_seconds: Time between warming cycles (default: 5 minutes)
        """
        logger.info(f"Starting scheduled cache warming (interval: {interval_seconds}s)")

        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self.warm_cache()

            except asyncio.CancelledError:
                logger.info("Scheduled cache warming cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduled cache warming: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache warming statistics

        Returns:
            Statistics dictionary
        """
        return {
            "warming_in_progress": self._warming_in_progress,
            "last_warm_time": self._last_warm_time.isoformat() if self._last_warm_time else None,
            "total_warmed": self._warm_count,
            "total_errors": self._warm_errors,
            "popular_symbols_count": len(self.popular_symbols),
        }


# Global cache warmer instance
cache_warmer = CacheWarmer()
