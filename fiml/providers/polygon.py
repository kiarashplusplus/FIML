"""
Polygon.io Provider Implementation
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError, ProviderTimeoutError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)


class PolygonProvider(BaseProvider):
    """
    Polygon.io data provider

    Provides:
    - Real-time and historical US stock data
    - Options data
    - Cryptocurrency data
    - Forex data
    - Low-latency WebSocket streams
    """

    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="polygon",
            enabled=True,
            priority=8,
            rate_limit_per_minute=60,  # Varies by plan
            timeout_seconds=10,
            api_key=api_key or settings.polygon_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize Polygon provider"""
        logger.info("Initializing Polygon provider")

        if not self.config.api_key:
            raise ProviderError("Polygon API key not configured")

        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("Polygon provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Polygon provider"""
        logger.info("Shutting down Polygon provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to Polygon"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

        if self.config.api_key:
            params["apiKey"] = self.config.api_key

        try:
            url = f"{self.BASE_URL}{endpoint}"
            async with self._session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                self._record_request()

                if response.status == 200:
                    data = await response.json()

                    # Check for API errors
                    if data.get("status") == "ERROR":
                        raise ProviderError(f"Polygon error: {data.get('error', 'Unknown error')}")

                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError("Polygon rate limit exceeded", retry_after=60)
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Polygon"""
        logger.info(f"Fetching price for {asset.symbol} from Polygon")

        try:
            endpoint = f"/v2/aggs/ticker/{asset.symbol}/prev"
            response_data = await self._make_request(endpoint)

            results = response_data.get("results", [])
            if not results:
                raise ProviderError(f"No price data available for {asset.symbol}")

            result = results[0]

            data = {
                "price": float(result.get("c", 0.0)),  # Close price
                "open": float(result.get("o", 0.0)),
                "high": float(result.get("h", 0.0)),
                "low": float(result.get("l", 0.0)),
                "volume": int(result.get("v", 0)),
                "vwap": float(result.get("vw", 0.0)),  # Volume weighted average price
                "timestamp": result.get("t", 0),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.98,
                metadata={"source": "polygon", "ticker": response_data.get("ticker")},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Polygon for {asset.symbol}: {e}")
            raise ProviderError(f"Polygon fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Polygon"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Polygon")

        try:
            # Map timeframe to Polygon format
            multiplier = 1
            timespan = "day"

            if timeframe == "1d":
                multiplier, timespan = 1, "day"
            elif timeframe in ["1h", "60min"]:
                multiplier, timespan = 1, "hour"
            elif timeframe == "5m":
                multiplier, timespan = 5, "minute"

            # Calculate date range
            from datetime import timedelta
            to_date = datetime.now(timezone.utc)
            from_date = to_date - timedelta(days=limit if timespan == "day" else 30)

            # Format endpoint with dates
            from_date_str = from_date.strftime('%Y-%m-%d')
            to_date_str = to_date.strftime('%Y-%m-%d')
            endpoint = (
                f"/v2/aggs/ticker/{asset.symbol}/range/{multiplier}/{timespan}/"
                f"{from_date_str}/{to_date_str}"
            )
            params = {"limit": str(limit), "sort": "desc"}

            response_data = await self._make_request(endpoint, params)

            results = response_data.get("results", [])
            if not results:
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            for bar in results[:limit]:
                ohlcv_data.append({
                    "timestamp": bar.get("t"),
                    "open": float(bar.get("o", 0.0)),
                    "high": float(bar.get("h", 0.0)),
                    "low": float(bar.get("l", 0.0)),
                    "close": float(bar.get("c", 0.0)),
                    "volume": int(bar.get("v", 0)),
                    "vwap": float(bar.get("vw", 0.0)),
                })

            data = {
                "ohlcv": ohlcv_data,
                "timeframe": timeframe,
                "count": len(ohlcv_data),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.OHLCV,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.98,
                metadata={"source": "polygon", "ticker": response_data.get("ticker")},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Polygon for {asset.symbol}: {e}")
            raise ProviderError(f"Polygon OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Polygon"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from Polygon")

        try:
            endpoint = f"/v3/reference/tickers/{asset.symbol}"
            response_data = await self._make_request(endpoint)

            results = response_data.get("results", {})
            if not results:
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            data = {
                "symbol": results.get("ticker", ""),
                "name": results.get("name", ""),
                "market": results.get("market", ""),
                "locale": results.get("locale", ""),
                "primary_exchange": results.get("primary_exchange", ""),
                "type": results.get("type", ""),
                "active": results.get("active", False),
                "currency_name": results.get("currency_name", ""),
                "market_cap": results.get("market_cap"),
                "phone_number": results.get("phone_number", ""),
                "address": results.get("address", {}),
                "description": results.get("description", ""),
                "homepage_url": results.get("homepage_url", ""),
                "total_employees": results.get("total_employees"),
                "list_date": results.get("list_date", ""),
                "share_class_shares_outstanding": results.get("share_class_shares_outstanding"),
                "weighted_shares_outstanding": results.get("weighted_shares_outstanding"),
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
                metadata={"source": "polygon"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from Polygon for {asset.symbol}: {e}")
            raise ProviderError(f"Polygon fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles from Polygon"""
        logger.info(f"Fetching news for {asset.symbol} from Polygon")

        try:
            endpoint = "/v2/reference/news"
            params = {
                "ticker": asset.symbol,
                "limit": str(limit),
            }

            response_data = await self._make_request(endpoint, params)

            results = response_data.get("results", [])

            articles = []
            for article in results[:limit]:
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("article_url", ""),
                    "publisher": article.get("publisher", {}).get("name", ""),
                    "published_at": article.get("published_utc", ""),
                    "author": article.get("author", ""),
                    "description": article.get("description", ""),
                    "amp_url": article.get("amp_url", ""),
                })

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.NEWS,
                data={"articles": articles},
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.92,
                metadata={"source": "polygon"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news from Polygon for {asset.symbol}: {e}")
            raise ProviderError(f"Polygon news fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Polygon supports US stocks, options, crypto, and forex
        return asset.asset_type in [AssetType.EQUITY, AssetType.CRYPTO, AssetType.FOREX, AssetType.OPTION]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.99,
            avg_latency_ms=80.0,  # Polygon is known for low latency
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
