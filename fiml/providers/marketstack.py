"""
Marketstack Provider Implementation
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


class MarketstackProvider(BaseProvider):
    """
    Marketstack data provider

    Provides:
    - Global stock data (170,000+ tickers, 70+ exchanges)
    - Real-time and historical data
    - End-of-day prices
    - Intraday data
    - Simple REST API integration
    """

    BASE_URL = "https://api.marketstack.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="marketstack",
            enabled=True,
            priority=6,
            rate_limit_per_minute=60,  # Varies by plan
            timeout_seconds=10,
            api_key=api_key or settings.marketstack_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize Marketstack provider"""
        logger.info("Initializing Marketstack provider")

        if not self.config.api_key:
            raise ProviderError("Marketstack API key not configured")

        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("Marketstack provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Marketstack provider"""
        logger.info("Shutting down Marketstack provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to Marketstack"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}
        
        params["access_key"] = self.config.api_key

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
                    if "error" in data:
                        raise ProviderError(f"Marketstack error: {data['error'].get('message', 'Unknown error')}")
                    
                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError("Marketstack rate limit exceeded", retry_after=60)
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Marketstack"""
        logger.info(f"Fetching price for {asset.symbol} from Marketstack")

        try:
            endpoint = "/eod/latest"
            params = {"symbols": asset.symbol}
            
            response_data = await self._make_request(endpoint, params)

            data_list = response_data.get("data", [])
            if not data_list:
                raise ProviderError(f"No price data available for {asset.symbol}")

            latest = data_list[0]
            
            data = {
                "price": float(latest.get("close", 0.0)),
                "open": float(latest.get("open", 0.0)),
                "high": float(latest.get("high", 0.0)),
                "low": float(latest.get("low", 0.0)),
                "volume": float(latest.get("volume", 0.0)),
                "date": latest.get("date", ""),
                "exchange": latest.get("exchange", ""),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.95,
                metadata={"source": "marketstack"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Marketstack for {asset.symbol}: {e}")
            raise ProviderError(f"Marketstack fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Marketstack"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Marketstack")

        try:
            # Use end-of-day endpoint for daily data
            endpoint = "/eod"
            params = {
                "symbols": asset.symbol,
                "limit": str(min(limit, 1000)),
            }
            
            response_data = await self._make_request(endpoint, params)

            data_list = response_data.get("data", [])
            if not data_list:
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            for bar in data_list[:limit]:
                ohlcv_data.append({
                    "timestamp": bar.get("date"),
                    "open": float(bar.get("open", 0.0)),
                    "high": float(bar.get("high", 0.0)),
                    "low": float(bar.get("low", 0.0)),
                    "close": float(bar.get("close", 0.0)),
                    "volume": float(bar.get("volume", 0.0)),
                    "adjusted_close": float(bar.get("adj_close", 0.0)),
                    "split_factor": float(bar.get("split_factor", 1.0)),
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
                metadata={"source": "marketstack"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Marketstack for {asset.symbol}: {e}")
            raise ProviderError(f"Marketstack OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Marketstack"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from Marketstack")

        # Marketstack doesn't provide extensive fundamental data
        # Return minimal data available from ticker info
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.FUNDAMENTALS,
            data={"symbol": asset.symbol, "note": "Limited fundamentals available"},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.5,
            metadata={"source": "marketstack", "note": "Limited fundamentals"},
        )

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles - Marketstack doesn't provide news"""
        # Marketstack doesn't have a news endpoint
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "marketstack", "note": "News not available"},
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Marketstack primarily supports equities and indices
        return asset.asset_type in [AssetType.EQUITY, AssetType.INDEX, AssetType.ETF]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.98,
            avg_latency_ms=150.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
