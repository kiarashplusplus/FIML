"""
CCXT Cryptocurrency Provider Implementation
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import ccxt.async_support as ccxt  # type: ignore[import-untyped]

from fiml.core.exceptions import (
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    RegionalRestrictionError,
)
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)

# Module-level constant for geo-blocking detection patterns
GEO_BLOCK_INDICATORS = [
    "cloudfront",
    "block access from your country",
    "access denied",
    "geographical",
    "geo-restrict",
    "region",
    "your country",
    "access from your location",
]


def _is_geo_blocked_error(error_message: str) -> bool:
    """
    Check if an error message indicates geo-blocking (CloudFront/CDN blocking).

    Some exchanges (like bybit) use CloudFront to geo-block certain regions,
    returning a 403 error that ccxt interprets as RateLimitExceeded.

    Args:
        error_message: The error message string to check

    Returns:
        True if the error appears to be geo-blocking related
    """
    error_lower = error_message.lower()
    return any(indicator in error_lower for indicator in GEO_BLOCK_INDICATORS)


class CCXTProvider(BaseProvider):
    """
    CCXT Cryptocurrency Provider

    Provides unified access to 100+ cryptocurrency exchanges:
    - Real-time price data
    - OHLCV data
    - Order book data
    - Trade data
    - Multi-exchange support (Binance, Coinbase, Kraken, etc.)
    """

    def __init__(self, exchange_id: str = "binance"):
        config = ProviderConfig(
            name=f"ccxt_{exchange_id}",
            enabled=True,
            priority=8,
            rate_limit_per_minute=100,  # Conservative default
            timeout_seconds=10,
        )
        super().__init__(config)
        self.exchange_id = exchange_id
        self._exchange: Optional[ccxt.Exchange] = None

    def _handle_ccxt_exception(
        self,
        exception: Exception,
        operation: str,
        asset_symbol: Optional[str] = None,
        record_error: bool = True,
    ) -> None:
        """
        Handle CCXT exceptions with proper error classification and logging.

        Args:
            exception: The caught exception
            operation: Description of the operation that failed (e.g., "initialization", "fetch_price")
            asset_symbol: Optional asset symbol for context in logging
            record_error: Whether to record the error in metrics (False during initialization)

        Raises:
            RegionalRestrictionError: If error indicates geo-blocking
            ProviderRateLimitError: If rate limit or DDoS protection triggered
            ProviderTimeoutError: If network or timeout error
            ProviderError: For other exchange errors
        """
        if record_error:
            self._record_error()

        error_msg = str(exception)

        # Handle rate limiting and DDoS protection (may include geo-blocking)
        if isinstance(exception, (ccxt.RateLimitExceeded, ccxt.DDoSProtection)):
            if _is_geo_blocked_error(error_msg):
                logger.warning(
                    f"Exchange {self.exchange_id} is geo-blocked or access denied",
                    exchange=self.exchange_id,
                    operation=operation,
                    asset=asset_symbol,
                    error=error_msg[:200],
                )
                raise RegionalRestrictionError(
                    f"Exchange {self.exchange_id} is not available in this region"
                )
            logger.warning(
                f"Rate limit or DDoS protection triggered on {self.exchange_id}",
                exchange=self.exchange_id,
                operation=operation,
                asset=asset_symbol,
                error=error_msg[:200],
            )
            raise ProviderRateLimitError(
                "Exchange rate limit exceeded",
                retry_after=60
            )

        # Handle maintenance mode
        if isinstance(exception, ccxt.OnMaintenance):
            logger.warning(
                f"Exchange {self.exchange_id} is under maintenance",
                exchange=self.exchange_id,
                operation=operation,
                error=error_msg[:200],
            )
            raise ProviderError(f"Exchange {self.exchange_id} is under maintenance")

        # Handle exchange unavailable
        if isinstance(exception, ccxt.ExchangeNotAvailable):
            logger.warning(
                f"Exchange {self.exchange_id} is not available",
                exchange=self.exchange_id,
                operation=operation,
                error=error_msg[:200],
            )
            raise ProviderError(f"Exchange {self.exchange_id} is currently unavailable")

        # Handle authentication errors
        if isinstance(exception, ccxt.AuthenticationError):
            logger.error(
                f"Authentication failed for exchange {self.exchange_id}",
                exchange=self.exchange_id,
                operation=operation,
                error=error_msg[:200],
            )
            raise ProviderError(f"Authentication failed for {self.exchange_id}")

        # Handle request timeout
        if isinstance(exception, ccxt.RequestTimeout):
            logger.warning(
                f"Request timeout on {self.exchange_id}",
                exchange=self.exchange_id,
                operation=operation,
                asset=asset_symbol,
                error=error_msg[:200],
            )
            raise ProviderTimeoutError(f"Request timeout: {exception}")

        # Handle network errors
        if isinstance(exception, ccxt.NetworkError):
            logger.error(
                f"Network error on {self.exchange_id}",
                exchange=self.exchange_id,
                operation=operation,
                asset=asset_symbol,
                error=error_msg[:200],
            )
            raise ProviderTimeoutError(f"Network error: {exception}")

        # Handle exchange errors (check for geo-blocking)
        if isinstance(exception, ccxt.ExchangeError):
            if _is_geo_blocked_error(error_msg):
                logger.warning(
                    f"Exchange {self.exchange_id} appears to be geo-blocked",
                    exchange=self.exchange_id,
                    operation=operation,
                    asset=asset_symbol,
                    error=error_msg[:200],
                )
                raise RegionalRestrictionError(
                    f"Exchange {self.exchange_id} is not available in this region"
                )
            logger.error(
                f"Exchange error on {self.exchange_id}",
                exchange=self.exchange_id,
                operation=operation,
                asset=asset_symbol,
                error=error_msg[:200],
            )
            raise ProviderError(f"Exchange error: {exception}")

        # Handle any other exception (check for geo-blocking)
        if _is_geo_blocked_error(error_msg):
            logger.warning(
                f"Exchange {self.exchange_id} appears to be geo-blocked",
                exchange=self.exchange_id,
                operation=operation,
                asset=asset_symbol,
                error=error_msg[:200],
            )
            raise RegionalRestrictionError(
                f"Exchange {self.exchange_id} is not available in this region"
            )
        logger.error(
            f"Error during {operation} on {self.exchange_id}",
            exchange=self.exchange_id,
            operation=operation,
            asset=asset_symbol,
            error=error_msg[:200],
        )
        raise ProviderError(f"CCXT {operation} failed: {exception}")

    async def initialize(self) -> None:
        """Initialize CCXT provider"""
        logger.info(f"Initializing CCXT provider with exchange: {self.exchange_id}")

        try:
            # Create exchange instance
            exchange_class = getattr(ccxt, self.exchange_id)
            self._exchange = exchange_class({
                'enableRateLimit': True,
                'timeout': self.config.timeout_seconds * 1000,  # milliseconds
            })

            # Load markets
            await self._exchange.load_markets()

            self._is_initialized = True
            logger.info(f"CCXT provider initialized with {len(self._exchange.markets)} markets")

        except Exception as e:
            # Use helper method for consistent error handling (don't record error during init)
            self._handle_ccxt_exception(e, operation="initialization", record_error=False)

    async def shutdown(self) -> None:
        """Shutdown CCXT provider"""
        logger.info(f"Shutting down CCXT provider ({self.exchange_id})")
        if self._exchange:
            await self._exchange.close()
        self._is_initialized = False

    def _normalize_symbol(self, asset: Asset) -> str:
        """Normalize symbol for CCXT format (e.g., BTC/USDT)"""
        # If asset already has pair format, use it
        if "/" in asset.symbol:
            return asset.symbol

        # Default to USDT pair for major coins
        return f"{asset.symbol.upper()}/USDT"

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from exchange"""
        if not self._exchange:
            raise ProviderError("Provider not initialized")

        self._record_request()
        logger.info(f"Fetching price for {asset.symbol} from {self.exchange_id}")

        try:
            symbol = self._normalize_symbol(asset)

            # Fetch ticker data
            ticker = await self._exchange.fetch_ticker(symbol)

            if not ticker:
                raise ProviderError(f"No ticker data for {symbol}")

            data = {
                "price": float(ticker.get("last", 0.0)),
                "bid": float(ticker.get("bid", 0.0)),
                "ask": float(ticker.get("ask", 0.0)),
                "high": float(ticker.get("high", 0.0)),
                "low": float(ticker.get("low", 0.0)),
                "open": float(ticker.get("open", 0.0)),
                "close": float(ticker.get("close", 0.0)),
                "volume": float(ticker.get("baseVolume", 0.0)),
                "quote_volume": float(ticker.get("quoteVolume", 0.0)),
                "change": float(ticker.get("change", 0.0) or 0.0),
                "change_percent": float(ticker.get("percentage", 0.0) or 0.0),
                "timestamp": ticker.get("timestamp", datetime.now(timezone.utc).timestamp() * 1000),
                "datetime": ticker.get("datetime", datetime.now(timezone.utc).isoformat()),
                "symbol": symbol,
                "info": ticker.get("info", {}),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.99,  # High confidence for real-time crypto data
                metadata={
                    "source": "ccxt",
                    "exchange": self.exchange_id,
                    "symbol": symbol,
                },
            )

        except ProviderError:
            # Re-raise ProviderError as-is (e.g., "No ticker data")
            raise
        except Exception as e:
            self._handle_ccxt_exception(e, operation="fetch_price", asset_symbol=asset.symbol)

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from exchange"""
        if not self._exchange:
            raise ProviderError("Provider not initialized")

        self._record_request()
        logger.info(f"Fetching OHLCV for {asset.symbol} from {self.exchange_id}")

        try:
            symbol = self._normalize_symbol(asset)

            # Map timeframe to CCXT format
            timeframe_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d",
                "1w": "1w",
            }
            ccxt_timeframe = timeframe_map.get(timeframe, "1d")

            # Fetch OHLCV data
            ohlcv = await self._exchange.fetch_ohlcv(
                symbol,
                timeframe=ccxt_timeframe,
                limit=limit
            )

            if not ohlcv:
                raise ProviderError(f"No OHLCV data for {symbol}")

            # Convert to standard format
            ohlcv_data = []
            for candle in ohlcv:
                # CCXT format: [timestamp, open, high, low, close, volume]
                ohlcv_data.append({
                    "timestamp": datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                })

            data = {
                "ohlcv": ohlcv_data,
                "timeframe": timeframe,
                "count": len(ohlcv_data),
                "symbol": symbol,
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.OHLCV,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.99,
                metadata={
                    "source": "ccxt",
                    "exchange": self.exchange_id,
                    "symbol": symbol,
                    "timeframe": ccxt_timeframe,
                },
            )

        except ProviderError:
            # Re-raise ProviderError as-is (e.g., "No OHLCV data")
            raise
        except Exception as e:
            self._handle_ccxt_exception(e, operation="fetch_ohlcv", asset_symbol=asset.symbol)

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """
        Fetch cryptocurrency fundamentals

        Note: Traditional fundamentals don't apply to crypto, but we can provide:
        - Market cap
        - Circulating supply
        - Total supply
        - Trading volume
        - Exchange info
        """
        if not self._exchange:
            raise ProviderError("Provider not initialized")

        self._record_request()
        logger.info(f"Fetching crypto metrics for {asset.symbol} from {self.exchange_id}")

        try:
            symbol = self._normalize_symbol(asset)

            # Fetch ticker for basic metrics
            ticker = await self._exchange.fetch_ticker(symbol)

            # Get market info
            market = self._exchange.market(symbol)

            data = {
                "symbol": symbol,
                "base": market.get("base", ""),
                "quote": market.get("quote", ""),
                "exchange": self.exchange_id,
                "active": market.get("active", True),
                "type": market.get("type", "spot"),
                "spot": market.get("spot", True),
                "future": market.get("future", False),
                "option": market.get("option", False),
                # Trading info
                "price": float(ticker.get("last", 0.0)),
                "volume_24h": float(ticker.get("baseVolume", 0.0)),
                "quote_volume_24h": float(ticker.get("quoteVolume", 0.0)),
                "high_24h": float(ticker.get("high", 0.0)),
                "low_24h": float(ticker.get("low", 0.0)),
                "change_24h": float(ticker.get("change", 0.0) or 0.0),
                "change_percent_24h": float(ticker.get("percentage", 0.0) or 0.0),
                # Market structure
                "maker_fee": float(market.get("maker", 0.0)),
                "taker_fee": float(market.get("taker", 0.0)),
                "precision_price": market.get("precision", {}).get("price", 8),
                "precision_amount": market.get("precision", {}).get("amount", 8),
                "min_amount": float(market.get("limits", {}).get("amount", {}).get("min", 0.0) or 0.0),
                "max_amount": float(market.get("limits", {}).get("amount", {}).get("max", 0.0) or 0.0),
                "min_cost": float(market.get("limits", {}).get("cost", {}).get("min", 0.0) or 0.0),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.FUNDAMENTALS,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.95,
                metadata={
                    "source": "ccxt",
                    "exchange": self.exchange_id,
                    "symbol": symbol,
                },
            )

        except ProviderError:
            # Re-raise ProviderError as-is
            raise
        except Exception as e:
            self._handle_ccxt_exception(e, operation="fetch_fundamentals", asset_symbol=asset.symbol)

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """
        Fetch news for cryptocurrency

        Note: Most CCXT exchanges don't provide news directly.
        This is a placeholder that could integrate with crypto news APIs.
        """
        logger.info(f"News fetch not supported by CCXT exchanges for {asset.symbol}")

        # Return empty news response
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={
                "source": "ccxt",
                "exchange": self.exchange_id,
                "note": "News not supported by exchange",
            },
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # CCXT supports crypto assets
        if asset.asset_type != AssetType.CRYPTO:
            return False

        if not self._exchange:
            return False

        # Check if symbol is in exchange markets
        try:
            symbol = self._normalize_symbol(asset)
            return symbol in self._exchange.markets
        except Exception:
            return False

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        try:
            # Check exchange status
            if self._exchange and hasattr(self._exchange, 'fetch_status'):
                status = await self._exchange.fetch_status()
                is_healthy = status.get('status') == 'ok'
            else:
                # Fallback: try fetching a common pair
                test_asset = Asset(symbol="BTC/USDT", asset_type=AssetType.CRYPTO)
                await self.fetch_price(test_asset)
                is_healthy = True

            return ProviderHealth(
                provider_name=self.name,
                is_healthy=is_healthy,
                uptime_percent=0.99,
                avg_latency_ms=50.0,  # Crypto exchanges are typically fast
                success_rate=1.0 - (self._error_count / max(self._request_count, 1)),
                last_check=datetime.now(timezone.utc),
                error_count_24h=self._error_count,
            )
        except Exception as e:
            logger.error(f"CCXT health check failed for {self.exchange_id}: {e}")
            return ProviderHealth(
                provider_name=self.name,
                is_healthy=False,
                uptime_percent=0.0,
                avg_latency_ms=0.0,
                success_rate=0.0,
                last_check=datetime.now(timezone.utc),
                error_count_24h=self._error_count,
            )

    async def health_check(self) -> ProviderHealth:
        """Check provider health"""
        try:
            # Check exchange status
            if self._exchange and hasattr(self._exchange, 'fetch_status'):
                status = await self._exchange.fetch_status()
                is_healthy = status.get('status') == 'ok'
            else:
                # Fallback: try fetching a common pair
                test_asset = Asset(symbol="BTC/USDT", asset_type=AssetType.CRYPTO)
                await self.fetch_price(test_asset)
                is_healthy = True

            return ProviderHealth(
                provider_name=self.name,
                is_healthy=is_healthy,
                uptime_percent=99.0,  # Placeholder
                avg_latency_ms=50.0,  # Crypto exchanges are typically fast
                success_rate=1.0 - (self._error_count / max(self._request_count, 1)),
                last_check=datetime.now(timezone.utc),
                error_count_24h=self._error_count,
            )
        except Exception as e:
            logger.error(f"CCXT health check failed for {self.exchange_id}: {e}")
            return ProviderHealth(
                provider_name=self.name,
                is_healthy=False,
                uptime_percent=0.0,
                avg_latency_ms=0.0,
                success_rate=0.0,
                last_check=datetime.now(timezone.utc),
                error_count_24h=self._error_count + 1,
            )

    def _record_request(self) -> None:
        """Record a successful request"""
        self._request_count += 1
        self._last_request_time = datetime.now(timezone.utc)

    def _record_error(self) -> None:
        """Record an error"""
        self._error_count += 1


class CCXTMultiExchangeProvider:
    """
    Manager for multiple CCXT exchanges

    Provides access to multiple exchanges and can aggregate data
    """

    def __init__(self, exchanges: Optional[List[str]] = None) -> None:
        if exchanges is None:
            exchanges = ["binance", "coinbase", "kraken"]

        self.exchanges = {
            exchange_id: CCXTProvider(exchange_id)
            for exchange_id in exchanges
        }

    async def initialize_all(self) -> None:
        """Initialize all exchanges"""
        await asyncio.gather(*[
            provider.initialize()
            for provider in self.exchanges.values()
        ])

    async def shutdown_all(self) -> None:
        """Shutdown all exchanges"""
        await asyncio.gather(*[
            provider.shutdown()
            for provider in self.exchanges.values()
        ])

    async def fetch_price_from_all(self, asset: Asset) -> List[ProviderResponse]:
        """Fetch price from all exchanges"""
        results = await asyncio.gather(*[
            provider.fetch_price(asset)
            for provider in self.exchanges.values()
        ], return_exceptions=True)

        # Filter out errors
        return [r for r in results if isinstance(r, ProviderResponse)]

    def get_provider(self, exchange_id: str) -> Optional[CCXTProvider]:
        """Get specific exchange provider"""
        return self.exchanges.get(exchange_id)
