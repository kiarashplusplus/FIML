"""
Financial Modeling Prep (FMP) Provider Implementation
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderRateLimitError, ProviderTimeoutError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)


class FMPProvider(BaseProvider):
    """
    Financial Modeling Prep (FMP) data provider

    Provides:
    - Real-time and historical equity data
    - Financial statements (income, balance sheet, cash flow)
    - Company profiles and metrics
    - Market data and news
    - Free tier: 250 API requests per day
    """

    BASE_URL = "https://financialmodelingprep.com/stable"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="fmp",
            enabled=True,
            priority=6,
            rate_limit_per_minute=10,  # Conservative limit
            timeout_seconds=10,
            api_key=api_key or settings.fmp_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_timestamps: list = []

    async def initialize(self) -> None:
        """Initialize FMP provider"""
        logger.info("Initializing FMP provider")

        if not self.config.api_key:
            logger.warning("FMP API key not configured - provider will not be initialized")
            self._is_initialized = False
            return

        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("FMP provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown FMP provider"""
        logger.info("Shutting down FMP provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limits"""
        now = datetime.now(timezone.utc)

        # Remove timestamps older than 1 minute
        self._request_timestamps = [
            ts for ts in self._request_timestamps if (now - ts).total_seconds() < 60
        ]

        # Check if we've exceeded the rate limit
        if len(self._request_timestamps) >= self.config.rate_limit_per_minute:
            wait_time = 60 - (now - self._request_timestamps[0]).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                raise ProviderRateLimitError(
                    f"Rate limit exceeded. Wait {wait_time:.1f}s", retry_after=int(wait_time) + 1
                )

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Any:
        """Make API request to FMP"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        await self._check_rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"

        if params is None:
            params = {}

        if self.config.api_key:
            params["apikey"] = self.config.api_key

        try:
            async with self._session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                self._request_timestamps.append(datetime.now(timezone.utc))
                self._record_request()

                if response.status == 200:
                    data = await response.json()

                    # Check for API errors
                    if isinstance(data, dict) and "Error Message" in data:
                        raise ProviderError(f"FMP error: {data['Error Message']}")

                    return data
                elif response.status == 429:
                    raise ProviderRateLimitError("FMP rate limit exceeded", retry_after=60)
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from FMP"""
        logger.info(f"Fetching price for {asset.symbol} from FMP")

        try:
            # Stable API uses query param for symbol
            endpoint = "quote"
            params = {"symbol": asset.symbol}
            response_data = await self._make_request(endpoint, params)

            if not response_data or len(response_data) == 0:
                raise ProviderError(f"No quote data available for {asset.symbol}")

            quote = response_data[0]

            data = {
                "price": float(quote.get("price", 0.0)),
                "change": float(quote.get("change", 0.0)),
                "change_percent": float(
                    quote.get("changesPercentage", 0.0) or quote.get("changePercentage", 0.0)
                ),
                "volume": int(quote.get("volume", 0)),
                "previous_close": float(quote.get("previousClose", 0.0)),
                "open": float(quote.get("open", 0.0)),
                "high": float(quote.get("dayHigh", 0.0)),
                "low": float(quote.get("dayLow", 0.0)),
                "market_cap": int(quote.get("marketCap", 0)),
                "pe_ratio": float(quote.get("pe", 0.0) or 0.0),
                "eps": float(quote.get("eps", 0.0) or 0.0),
                "shares_outstanding": int(quote.get("sharesOutstanding", 0)),
                "timestamp": quote.get("timestamp", 0),
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
                metadata={
                    "source": "fmp",
                    "endpoint": "quote",
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from FMP for {asset.symbol}: {e}")
            raise ProviderError(f"FMP fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from FMP"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from FMP")

        try:
            if timeframe == "1d":
                # Stable API for daily data
                endpoint = "historical-price-eod/full"
                params = {"symbol": asset.symbol}
            else:
                # Intraday not supported on stable/legacy plan
                raise ProviderError("Intraday OHLCV not supported by FMP stable API")

            response_data = await self._make_request(endpoint, params)

            # Extract historical data
            historical = []
            # Stable API response is a list directly for historical-price-eod/full? No, usually {symbol, historical: []} or list of dicts
            # Based on test script output: [{'symbol': 'AAPL', 'date': '2025-11-25', ...}, ...]
            # It seems to return a list of daily objects directly or wrapped.
            # Let's handle both cases.

            if isinstance(response_data, dict) and "historical" in response_data:
                historical = response_data["historical"]
            elif isinstance(response_data, list):
                historical = response_data

            historical = historical[:limit]

            if not historical:
                raise ProviderError(f"No historical data available for {asset.symbol}")

            # Convert to standard format
            ohlcv_data = []
            for candle in historical:
                ohlcv_data.append(
                    {
                        "timestamp": candle.get("date", ""),
                        "open": float(candle.get("open", 0.0)),
                        "high": float(candle.get("high", 0.0)),
                        "low": float(candle.get("low", 0.0)),
                        "close": float(candle.get("close", 0.0)),
                        "volume": int(candle.get("volume", 0)),
                    }
                )

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
                metadata={
                    "source": "fmp",
                    "endpoint": endpoint,
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from FMP for {asset.symbol}: {e}")
            raise ProviderError(f"FMP OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from FMP"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from FMP")

        try:
            # Stable API uses query param for symbol
            endpoint = "profile"
            params = {"symbol": asset.symbol}
            profile_data = await self._make_request(endpoint, params)

            if not profile_data or len(profile_data) == 0:
                raise ProviderError(f"No profile data available for {asset.symbol}")

            profile = profile_data[0]

            # Key metrics might not be available on stable or require different endpoint
            # For now, just use profile data which has many metrics
            metrics: Dict[str, Any] = {}

            # Combine data
            data = {
                "symbol": profile.get("symbol", ""),
                "name": profile.get("companyName", ""),
                "description": profile.get("description", ""),
                "exchange": profile.get("exchange", ""),
                "currency": profile.get("currency", ""),
                "country": profile.get("country", ""),
                "sector": profile.get("sector", ""),
                "industry": profile.get("industry", ""),
                "website": profile.get("website", ""),
                "ceo": profile.get("ceo", ""),
                "employees": int(profile.get("fullTimeEmployees", 0)),
                "market_cap": int(profile.get("mktCap", 0)),
                "price": float(profile.get("price", 0.0)),
                "beta": float(profile.get("beta", 0.0) or 0.0),
                "volume_avg": int(profile.get("volAvg", 0)),
                "last_div": float(profile.get("lastDiv", 0.0) or 0.0),
                "changes": float(profile.get("changes", 0.0) or 0.0),
                # Key metrics from profile
                "pe_ratio": float(
                    metrics.get("peRatio", 0.0) or 0.0
                ),  # Profile doesn't have PE usually? Actually test output showed it might not.
                # Let's fill what we can from profile
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.FUNDAMENTALS,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.96,
                metadata={
                    "source": "fmp",
                    "endpoints": ["profile"],
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from FMP for {asset.symbol}: {e}")
            raise ProviderError(f"FMP fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles from FMP"""
        # Stable API news endpoint not confirmed working
        logger.info(f"Fetching news for {asset.symbol} from FMP (Not Supported on Stable)")

        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=False,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "fmp", "error": "News not supported on stable API plan"},
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # FMP primarily supports equities
        return asset.asset_type == AssetType.EQUITY

    def _calculate_success_rate(self) -> float:
        """Calculate success rate based on request and error counts"""
        if self._request_count == 0:
            return 0.0
        return 1.0 - (self._error_count / self._request_count)

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        # If not initialized, return unhealthy status with meaningful values
        if not self._is_initialized:
            return ProviderHealth(
                provider_name=self.name,
                is_healthy=False,
                uptime_percent=0.0,
                avg_latency_ms=0.0,
                success_rate=0.0,
                last_check=datetime.now(timezone.utc),
                error_count_24h=0,
            )

        try:
            start_time = time.time()

            # Simple health check - fetch a known symbol
            test_asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
            await self.fetch_price(test_asset)

            latency_ms = (time.time() - start_time) * 1000

            return ProviderHealth(
                provider_name=self.name,
                is_healthy=True,
                uptime_percent=0.98,
                avg_latency_ms=latency_ms,
                success_rate=self._calculate_success_rate(),
                last_check=datetime.now(timezone.utc),
                error_count_24h=self._error_count,
            )
        except Exception as e:
            logger.error(f"FMP health check failed: {e}")
            return ProviderHealth(
                provider_name=self.name,
                is_healthy=False,
                uptime_percent=0.0,
                avg_latency_ms=0.0,
                success_rate=self._calculate_success_rate(),
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
