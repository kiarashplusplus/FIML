"""
Finnhub Provider Implementation
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


class FinnhubProvider(BaseProvider):
    """
    Finnhub data provider

    Provides:
    - Real-time global stock data
    - Forex data
    - Cryptocurrency data
    - Company fundamentals
    - News and sentiment
    - Economic indicators
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="finnhub",
            enabled=True,
            priority=7,
            rate_limit_per_minute=60,  # Free tier: 60 calls/minute
            timeout_seconds=10,
            api_key=api_key or settings.finnhub_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize Finnhub provider"""
        logger.info("Initializing Finnhub provider")

        if not self.config.api_key:
            raise ProviderError("Finnhub API key not configured")

        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("Finnhub provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Finnhub provider"""
        logger.info("Shutting down Finnhub provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to Finnhub"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

        params["token"] = self.config.api_key

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
                    if isinstance(data, dict) and data.get("error"):
                        raise ProviderError(f"Finnhub error: {data.get('error')}")

                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError("Finnhub rate limit exceeded", retry_after=60)
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Finnhub"""
        logger.info(f"Fetching price for {asset.symbol} from Finnhub")

        try:
            endpoint = "/quote"
            params = {"symbol": asset.symbol}

            response_data = await self._make_request(endpoint, params)

            if not response_data or response_data.get("c") == 0:
                raise ProviderError(f"No price data available for {asset.symbol}")

            data = {
                "price": float(response_data.get("c", 0.0)),  # Current price
                "change": float(response_data.get("d", 0.0)),  # Change
                "change_percent": float(response_data.get("dp", 0.0)),  # Percent change
                "high": float(response_data.get("h", 0.0)),  # High price of the day
                "low": float(response_data.get("l", 0.0)),  # Low price of the day
                "open": float(response_data.get("o", 0.0)),  # Open price of the day
                "previous_close": float(response_data.get("pc", 0.0)),  # Previous close price
                "timestamp": int(response_data.get("t", 0)),  # UNIX timestamp
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.96,
                metadata={"source": "finnhub"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Finnhub for {asset.symbol}: {e}")
            raise ProviderError(f"Finnhub fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Finnhub"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Finnhub")

        try:
            # Map timeframe to resolution
            resolution_map = {
                "1d": "D",
                "1h": "60",
                "5m": "5",
            }
            resolution = resolution_map.get(timeframe, "D")

            # Calculate time range
            from datetime import timedelta
            to_timestamp = int(datetime.now(timezone.utc).timestamp())

            # Adjust lookback based on timeframe
            if timeframe == "1d":
                from_timestamp = int((datetime.now(timezone.utc) - timedelta(days=limit)).timestamp())
            elif timeframe == "1h":
                from_timestamp = int((datetime.now(timezone.utc) - timedelta(hours=limit)).timestamp())
            else:
                from_timestamp = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())

            endpoint = "/stock/candle"
            params = {
                "symbol": asset.symbol,
                "resolution": resolution,
                "from": str(from_timestamp),
                "to": str(to_timestamp),
            }

            response_data = await self._make_request(endpoint, params)

            if response_data.get("s") == "no_data":
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            timestamps = response_data.get("t", [])
            opens = response_data.get("o", [])
            highs = response_data.get("h", [])
            lows = response_data.get("l", [])
            closes = response_data.get("c", [])
            volumes = response_data.get("v", [])

            for i in range(min(len(timestamps), limit)):
                ohlcv_data.append({
                    "timestamp": timestamps[i],
                    "open": float(opens[i]),
                    "high": float(highs[i]),
                    "low": float(lows[i]),
                    "close": float(closes[i]),
                    "volume": int(volumes[i]),
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
                confidence=0.96,
                metadata={"source": "finnhub"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Finnhub for {asset.symbol}: {e}")
            raise ProviderError(f"Finnhub OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Finnhub"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from Finnhub")

        try:
            # Get company profile
            endpoint = "/stock/profile2"
            params = {"symbol": asset.symbol}

            response_data = await self._make_request(endpoint, params)

            if not response_data or not response_data.get("ticker"):
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            # Get basic financials
            metrics_endpoint = "/stock/metric"
            metrics_params = {"symbol": asset.symbol, "metric": "all"}
            metrics_data = await self._make_request(metrics_endpoint, metrics_params)

            metric = metrics_data.get("metric", {})

            data = {
                "symbol": response_data.get("ticker", ""),
                "name": response_data.get("name", ""),
                "country": response_data.get("country", ""),
                "currency": response_data.get("currency", ""),
                "exchange": response_data.get("exchange", ""),
                "ipo": response_data.get("ipo", ""),
                "market_cap": float(response_data.get("marketCapitalization", 0.0)) * 1_000_000,  # Convert to actual value
                "phone": response_data.get("phone", ""),
                "share_outstanding": float(response_data.get("shareOutstanding", 0.0)) * 1_000_000,
                "website": response_data.get("weburl", ""),
                "logo": response_data.get("logo", ""),
                "industry": response_data.get("finnhubIndustry", ""),
                # Metrics
                "52_week_high": metric.get("52WeekHigh"),
                "52_week_low": metric.get("52WeekLow"),
                "beta": metric.get("beta"),
                "pe_ratio": metric.get("peBasicExclExtraTTM"),
                "eps": metric.get("epsBasicExclExtraItemsTTM"),
                "dividend_yield": metric.get("dividendYieldIndicatedAnnual"),
                "roe": metric.get("roeTTM"),
                "roa": metric.get("roaTTM"),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.FUNDAMENTALS,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.94,
                metadata={"source": "finnhub"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from Finnhub for {asset.symbol}: {e}")
            raise ProviderError(f"Finnhub fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles from Finnhub"""
        logger.info(f"Fetching news for {asset.symbol} from Finnhub")

        try:
            # Get current and previous dates for news range
            from datetime import timedelta
            to_date = datetime.now(timezone.utc)
            from_date = to_date - timedelta(days=7)

            endpoint = "/company-news"
            params = {
                "symbol": asset.symbol,
                "from": from_date.strftime("%Y-%m-%d"),
                "to": to_date.strftime("%Y-%m-%d"),
            }

            response_data = await self._make_request(endpoint, params)

            if not isinstance(response_data, list):
                raise ProviderError("Unexpected response format for news")

            articles = []
            for article in response_data[:limit]:
                articles.append({
                    "title": article.get("headline", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "published_at": datetime.fromtimestamp(article.get("datetime", 0), tz=timezone.utc).isoformat(),
                    "summary": article.get("summary", ""),
                    "category": article.get("category", ""),
                    "image": article.get("image", ""),
                })

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.NEWS,
                data={"articles": articles},
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.93,
                metadata={"source": "finnhub"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news from Finnhub for {asset.symbol}: {e}")
            raise ProviderError(f"Finnhub news fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Finnhub supports equities, forex, and crypto
        return asset.asset_type in [AssetType.EQUITY, AssetType.FOREX, AssetType.CRYPTO]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.98,
            avg_latency_ms=120.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
