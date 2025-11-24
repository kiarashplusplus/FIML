"""
Twelvedata Provider Implementation
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


class TwelvedataProvider(BaseProvider):
    """
    Twelvedata provider

    Provides:
    - Global stock data (100,000+ symbols)
    - Forex data
    - ETF data
    - Cryptocurrency data
    - Technical indicators
    - Real-time WebSocket streams
    """

    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="twelvedata",
            enabled=True,
            priority=7,
            rate_limit_per_minute=8,  # Free tier: 8 calls/minute
            timeout_seconds=10,
            api_key=api_key or settings.twelvedata_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize Twelvedata provider"""
        logger.info("Initializing Twelvedata provider")

        if not self.config.api_key:
            raise ProviderError("Twelvedata API key not configured")

        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("Twelvedata provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Twelvedata provider"""
        logger.info("Shutting down Twelvedata provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to Twelvedata"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

        params["apikey"] = self.config.api_key

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
                    if isinstance(data, dict) and data.get("status") == "error":
                        raise ProviderError(f"Twelvedata error: {data.get('message', 'Unknown error')}")

                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError("Twelvedata rate limit exceeded", retry_after=60)
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Twelvedata"""
        logger.info(f"Fetching price for {asset.symbol} from Twelvedata")

        try:
            endpoint = "/price"
            params = {"symbol": asset.symbol}

            response_data = await self._make_request(endpoint, params)

            if not response_data or "price" not in response_data:
                raise ProviderError(f"No price data available for {asset.symbol}")

            # Also get quote for additional data
            quote_endpoint = "/quote"
            quote_params = {"symbol": asset.symbol}
            quote_data = await self._make_request(quote_endpoint, quote_params)

            data = {
                "price": float(response_data.get("price", 0.0)),
                "open": float(quote_data.get("open", 0.0)),
                "high": float(quote_data.get("high", 0.0)),
                "low": float(quote_data.get("low", 0.0)),
                "close": float(quote_data.get("close", 0.0)),
                "volume": int(quote_data.get("volume", 0)),
                "change": float(quote_data.get("change", 0.0)),
                "change_percent": float(quote_data.get("percent_change", 0.0)),
                "previous_close": float(quote_data.get("previous_close", 0.0)),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.97,
                metadata={"source": "twelvedata"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Twelvedata for {asset.symbol}: {e}")
            raise ProviderError(f"Twelvedata fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Twelvedata"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Twelvedata")

        try:
            # Map timeframe to interval
            interval_map = {
                "1d": "1day",
                "1h": "1h",
                "5m": "5min",
            }
            interval = interval_map.get(timeframe, "1day")

            endpoint = "/time_series"
            params = {
                "symbol": asset.symbol,
                "interval": interval,
                "outputsize": str(min(limit, 5000)),  # Max 5000
            }

            response_data = await self._make_request(endpoint, params)

            values = response_data.get("values", [])
            if not values:
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            for bar in values[:limit]:
                ohlcv_data.append({
                    "timestamp": bar.get("datetime"),
                    "open": float(bar.get("open", 0.0)),
                    "high": float(bar.get("high", 0.0)),
                    "low": float(bar.get("low", 0.0)),
                    "close": float(bar.get("close", 0.0)),
                    "volume": int(bar.get("volume", 0)),
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
                confidence=0.97,
                metadata={"source": "twelvedata"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Twelvedata for {asset.symbol}: {e}")
            raise ProviderError(f"Twelvedata OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Twelvedata"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from Twelvedata")

        try:
            # Get company profile
            endpoint = "/profile"
            params = {"symbol": asset.symbol}

            response_data = await self._make_request(endpoint, params)

            if not response_data or response_data.get("status") == "error":
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            # Get statistics
            stats_endpoint = "/statistics"
            stats_params = {"symbol": asset.symbol}
            stats_data = await self._make_request(stats_endpoint, stats_params)
            statistics = stats_data.get("statistics", {})
            valuations = statistics.get("valuations_metrics", {})

            data = {
                "symbol": response_data.get("symbol", ""),
                "name": response_data.get("name", ""),
                "exchange": response_data.get("exchange", ""),
                "currency": response_data.get("currency", ""),
                "country": response_data.get("country", ""),
                "type": response_data.get("type", ""),
                "sector": response_data.get("sector", ""),
                "industry": response_data.get("industry", ""),
                "website": response_data.get("website", ""),
                "description": response_data.get("description", ""),
                "ceo": response_data.get("ceo", ""),
                "employees": response_data.get("employees"),
                "market_cap": valuations.get("market_capitalization"),
                "pe_ratio": valuations.get("pe_ratio"),
                "peg_ratio": valuations.get("peg_ratio"),
                "book_value": valuations.get("book_value"),
                "dividend_yield": valuations.get("dividend_yield"),
                "eps": valuations.get("earnings_per_share"),
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
                metadata={"source": "twelvedata"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from Twelvedata for {asset.symbol}: {e}")
            raise ProviderError(f"Twelvedata fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles from Twelvedata"""
        logger.info(f"Fetching news for {asset.symbol} from Twelvedata")

        # Twelvedata doesn't have a dedicated news endpoint in free tier
        # Return empty news with appropriate metadata
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "twelvedata", "note": "News not available in this tier"},
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Twelvedata supports stocks, forex, ETF, and crypto
        return asset.asset_type in [AssetType.EQUITY, AssetType.FOREX, AssetType.ETF, AssetType.CRYPTO]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.995,  # Twelvedata has 99.95% uptime
            avg_latency_ms=100.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
