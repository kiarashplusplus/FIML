"""
Quandl (NASDAQ Data Link) Provider Implementation
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


class QuandlProvider(BaseProvider):
    """
    Quandl (NASDAQ Data Link) provider

    Provides:
    - Historical financial data
    - Economic indicators
    - Alternative data
    - Fundamental data
    - Commodity prices
    - Used for quant and academic research
    """

    BASE_URL = "https://data.nasdaq.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="quandl",
            enabled=True,
            priority=6,
            rate_limit_per_minute=50,  # Free tier: 50 calls/day
            timeout_seconds=10,
            api_key=api_key or settings.quandl_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize Quandl provider"""
        logger.info("Initializing Quandl provider")

        if not self.config.api_key:
            raise ProviderError("Quandl API key not configured")

        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("Quandl provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Quandl provider"""
        logger.info("Shutting down Quandl provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to Quandl"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

        if self.config.api_key:
            params["api_key"] = self.config.api_key

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
                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError("Quandl rate limit exceeded", retry_after=60)
                elif response.status == 404:
                    raise ProviderError("Data not found")
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Quandl"""
        logger.info(f"Fetching price for {asset.symbol} from Quandl")

        try:
            # Quandl uses database/dataset format, e.g., WIKI/AAPL
            # Try common databases
            database = "WIKI"  # Free wiki database (end-of-day prices, historical)

            endpoint = f"/datasets/{database}/{asset.symbol}.json"
            params = {"rows": "1"}  # Get most recent data

            response_data = await self._make_request(endpoint, params)

            dataset = response_data.get("dataset", {})
            data_points = dataset.get("data", [])

            if not data_points:
                raise ProviderError(f"No price data available for {asset.symbol}")

            # Data format: [Date, Open, High, Low, Close, Volume, ...]
            latest = data_points[0]

            data = {
                "date": latest[0],
                "open": float(latest[1]) if latest[1] is not None else 0.0,
                "high": float(latest[2]) if latest[2] is not None else 0.0,
                "low": float(latest[3]) if latest[3] is not None else 0.0,
                "price": float(latest[4]) if latest[4] is not None else 0.0,  # Close
                "volume": float(latest[5]) if latest[5] is not None else 0.0,
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=False,  # Quandl WIKI data is historical, not real-time
                confidence=0.90,
                metadata={
                    "source": "quandl",
                    "database": database,
                    "note": "Historical data only, not real-time",
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Quandl for {asset.symbol}: {e}")
            raise ProviderError(f"Quandl fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Quandl"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Quandl")

        try:
            database = "WIKI"

            endpoint = f"/datasets/{database}/{asset.symbol}.json"
            params = {"rows": str(limit)}

            response_data = await self._make_request(endpoint, params)

            dataset = response_data.get("dataset", {})
            data_points = dataset.get("data", [])

            if not data_points:
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            for point in data_points:
                ohlcv_data.append({
                    "timestamp": point[0],
                    "open": float(point[1]) if point[1] is not None else 0.0,
                    "high": float(point[2]) if point[2] is not None else 0.0,
                    "low": float(point[3]) if point[3] is not None else 0.0,
                    "close": float(point[4]) if point[4] is not None else 0.0,
                    "volume": float(point[5]) if point[5] is not None else 0.0,
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
                is_fresh=False,
                confidence=0.90,
                metadata={
                    "source": "quandl",
                    "database": database,
                    "note": "Historical data",
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Quandl for {asset.symbol}: {e}")
            raise ProviderError(f"Quandl OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Quandl"""
        # Quandl doesn't have a standard fundamentals endpoint
        # Would need specific database access
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.FUNDAMENTALS,
            data={"note": "Fundamentals require specific database subscription"},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "quandl"},
        )

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles - Quandl doesn't provide news"""
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "quandl", "note": "News not available"},
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Quandl primarily supports equities and economic data
        return asset.asset_type in [AssetType.EQUITY, AssetType.INDEX, AssetType.COMMODITY]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.98,
            avg_latency_ms=200.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
