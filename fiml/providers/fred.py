"""
FRED (Federal Reserve Economic Data) Provider Implementation
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


class FredProvider(BaseProvider):
    """
    FRED (Federal Reserve Economic Data) provider

    Provides:
    - Macroeconomic indicators (GDP, CPI, Unemployment, Interest Rates)
    - Economic data series
    """

    BASE_URL = "https://api.stlouisfed.org/fred"

    # Mapping of common macro indicators to FRED series IDs
    SERIES_MAPPING = {
        "GDP": "GDP",
        "CPI": "CPIAUCSL",  # Consumer Price Index for All Urban Consumers: All Items
        "UNEMPLOYMENT": "UNRATE",  # Unemployment Rate
        "INTEREST_RATE": "FEDFUNDS",  # Federal Funds Effective Rate
        "INFLATION": "CPIAUCSL",  # Use CPI for inflation calculation
        "10Y_TREASURY": "DGS10",  # Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity
        "VIX": "VIXCLS",  # CBOE Volatility Index
        "M2": "M2SL",  # M2 Money Stock
    }

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="fred",
            enabled=True,
            priority=8,  # High priority for macro data
            rate_limit_per_minute=120,
            timeout_seconds=10,
            api_key=api_key or settings.fred_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize FRED provider"""
        logger.info("Initializing FRED provider")

        if not self.config.api_key:
            raise ProviderError("FRED API key not configured")

        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("FRED provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown FRED provider"""
        logger.info("Shutting down FRED provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make API request to FRED"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

        if self.config.api_key:
            params["api_key"] = self.config.api_key

        params["file_type"] = "json"

        try:
            url = f"{self.BASE_URL}{endpoint}"
            async with self._session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                self._record_request()

                if response.status == 200:
                    data = await response.json()
                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError("FRED rate limit exceeded", retry_after=60)
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

    async def fetch_macro(self, asset: Asset) -> ProviderResponse:
        """Fetch macro economic data"""
        logger.info(f"Fetching macro data for {asset.symbol} from FRED")

        try:
            # Determine series ID
            series_id = self.SERIES_MAPPING.get(asset.symbol.upper())
            if not series_id:
                # If not in mapping, assume symbol is the series ID
                series_id = asset.symbol

            endpoint = "/series/observations"
            params = {
                "series_id": series_id,
                "sort_order": "desc",
                "limit": "1",  # Get most recent
            }

            response_data = await self._make_request(endpoint, params)
            observations = response_data.get("observations", [])

            if not observations:
                raise ProviderError(f"No macro data available for {asset.symbol}")

            latest = observations[0]

            # Parse value (handle "." which FRED uses for missing data)
            value_str = latest.get("value", ".")
            try:
                value = float(value_str)
            except ValueError:
                value = 0.0

            data = {
                "value": value,
                "date": latest.get("date"),
                "series_id": series_id,
                "unit": "unknown",  # Would need metadata endpoint to get units
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.MACRO,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.95,
                metadata={
                    "source": "fred",
                    "series_id": series_id,
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching macro data from FRED for {asset.symbol}: {e}")
            raise ProviderError(f"FRED fetch failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch price (treat macro series value as price)"""
        # For macro assets, price is the value
        try:
            macro_response = await self.fetch_macro(asset)

            data = {
                "price": macro_response.data.get("value", 0.0),
                "date": macro_response.data.get("date"),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=macro_response.timestamp,
                is_valid=macro_response.is_valid,
                is_fresh=macro_response.is_fresh,
                confidence=macro_response.confidence,
                metadata=macro_response.metadata,
            )
        except Exception as e:
            raise ProviderError(f"FRED price fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch historical series data as OHLCV (Close only)"""
        logger.info(f"Fetching historical series for {asset.symbol} from FRED")

        try:
            series_id = self.SERIES_MAPPING.get(asset.symbol.upper(), asset.symbol)
            endpoint = "/series/observations"
            params = {
                "series_id": series_id,
                "sort_order": "desc",
                "limit": str(limit),
            }

            response_data = await self._make_request(endpoint, params)
            observations = response_data.get("observations", [])

            if not observations:
                raise ProviderError(f"No historical data available for {asset.symbol}")

            ohlcv_data = []
            for obs in observations:
                try:
                    val = float(obs.get("value", "."))
                except ValueError:
                    continue

                ohlcv_data.append({
                    "timestamp": obs.get("date"),
                    "open": val,
                    "high": val,
                    "low": val,
                    "close": val,
                    "volume": 0,
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
                confidence=0.95,
                metadata={
                    "source": "fred",
                    "series_id": series_id,
                },
            )

        except Exception as e:
            self._record_error()
            raise ProviderError(f"FRED historical fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.FUNDAMENTALS,
            data={},
            timestamp=datetime.now(timezone.utc),
            is_valid=False,
            metadata={"error": "Not supported"},
        )

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={},
            timestamp=datetime.now(timezone.utc),
            is_valid=False,
            metadata={"error": "Not supported"},
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # FRED supports economic indicators (INDEX) and potentially commodities
        return asset.asset_type in [AssetType.INDEX, AssetType.COMMODITY] or asset.symbol in self.SERIES_MAPPING

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.99,
            avg_latency_ms=150.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
