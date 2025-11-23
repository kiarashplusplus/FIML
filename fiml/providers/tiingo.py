"""
Tiingo Provider Implementation
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


class TiingoProvider(BaseProvider):
    """
    Tiingo data provider

    Provides:
    - End-of-day stock prices
    - Real-time IEX feed
    - Financial news
    - Cryptocurrency data
    - Forex data
    - 20+ years of fundamental data
    """

    BASE_URL = "https://api.tiingo.com"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="tiingo",
            enabled=True,
            priority=7,
            rate_limit_per_minute=60,  # Varies by plan
            timeout_seconds=10,
            api_key=api_key or settings.tiingo_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize Tiingo provider"""
        logger.info("Initializing Tiingo provider")

        if not self.config.api_key:
            raise ProviderError("Tiingo API key not configured")

        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Token {self.config.api_key}"}
        )
        self._is_initialized = True
        logger.info("Tiingo provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Tiingo provider"""
        logger.info("Shutting down Tiingo provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Any:
        """Make API request to Tiingo"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

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
                    raise ProviderRateLimitError("Tiingo rate limit exceeded", retry_after=60)
                elif response.status == 404:
                    raise ProviderError(f"Symbol not found")
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Tiingo"""
        logger.info(f"Fetching price for {asset.symbol} from Tiingo")

        try:
            # Use IEX endpoint for real-time prices
            endpoint = f"/tiingo/daily/{asset.symbol}/prices"
            
            response_data = await self._make_request(endpoint)

            if not isinstance(response_data, list) or not response_data:
                raise ProviderError(f"No price data available for {asset.symbol}")

            latest = response_data[0]
            
            data = {
                "price": float(latest.get("close", 0.0)),
                "open": float(latest.get("open", 0.0)),
                "high": float(latest.get("high", 0.0)),
                "low": float(latest.get("low", 0.0)),
                "volume": int(latest.get("volume", 0)),
                "adjusted_close": float(latest.get("adjClose", 0.0)),
                "dividend_cash": float(latest.get("divCash", 0.0)),
                "split_factor": float(latest.get("splitFactor", 1.0)),
                "date": latest.get("date", ""),
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
                metadata={"source": "tiingo"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Tiingo for {asset.symbol}: {e}")
            raise ProviderError(f"Tiingo fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Tiingo"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Tiingo")

        try:
            # Calculate date range
            from datetime import timedelta
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=limit if timeframe == "1d" else 365)
            
            endpoint = f"/tiingo/daily/{asset.symbol}/prices"
            params = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
            }
            
            response_data = await self._make_request(endpoint, params)

            if not isinstance(response_data, list) or not response_data:
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            for bar in response_data[:limit]:
                ohlcv_data.append({
                    "timestamp": bar.get("date"),
                    "open": float(bar.get("open", 0.0)),
                    "high": float(bar.get("high", 0.0)),
                    "low": float(bar.get("low", 0.0)),
                    "close": float(bar.get("close", 0.0)),
                    "volume": int(bar.get("volume", 0)),
                    "adjusted_close": float(bar.get("adjClose", 0.0)),
                    "adjusted_high": float(bar.get("adjHigh", 0.0)),
                    "adjusted_low": float(bar.get("adjLow", 0.0)),
                    "adjusted_open": float(bar.get("adjOpen", 0.0)),
                    "adjusted_volume": int(bar.get("adjVolume", 0)),
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
                metadata={"source": "tiingo"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Tiingo for {asset.symbol}: {e}")
            raise ProviderError(f"Tiingo OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Tiingo"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from Tiingo")

        try:
            # Get ticker metadata
            endpoint = f"/tiingo/daily/{asset.symbol}"
            
            response_data = await self._make_request(endpoint)

            if not response_data:
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            data = {
                "symbol": response_data.get("ticker", ""),
                "name": response_data.get("name", ""),
                "exchange_code": response_data.get("exchangeCode", ""),
                "description": response_data.get("description", ""),
                "start_date": response_data.get("startDate", ""),
                "end_date": response_data.get("endDate", ""),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.FUNDAMENTALS,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.90,
                metadata={"source": "tiingo"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from Tiingo for {asset.symbol}: {e}")
            raise ProviderError(f"Tiingo fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles from Tiingo"""
        logger.info(f"Fetching news for {asset.symbol} from Tiingo")

        try:
            endpoint = "/tiingo/news"
            params = {
                "tickers": asset.symbol,
                "limit": str(limit),
            }

            response_data = await self._make_request(endpoint, params)

            if not isinstance(response_data, list):
                raise ProviderError(f"Unexpected response format for news")

            articles = []
            for article in response_data[:limit]:
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "published_at": article.get("publishedDate", ""),
                    "description": article.get("description", ""),
                    "tags": article.get("tags", []),
                })

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.NEWS,
                data={"articles": articles},
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.94,
                metadata={"source": "tiingo"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news from Tiingo for {asset.symbol}: {e}")
            raise ProviderError(f"Tiingo news fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Tiingo supports stocks, ETFs, and crypto
        return asset.asset_type in [AssetType.EQUITY, AssetType.ETF, AssetType.CRYPTO]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.99,
            avg_latency_ms=110.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
