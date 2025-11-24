"""
Intrinio Provider Implementation
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


class IntrinioProvider(BaseProvider):
    """
    Intrinio data provider

    Provides:
    - US stock data
    - Options data (without full OPRA licensing)
    - Historical and real-time prices
    - Company fundamentals (standardized and as-reported)
    - Press releases and news
    - Analyst estimates
    - ESG ratings
    """

    BASE_URL = "https://api-v2.intrinio.com"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="intrinio",
            enabled=True,
            priority=7,
            rate_limit_per_minute=60,  # Varies by plan
            timeout_seconds=10,
            api_key=api_key or settings.intrinio_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize Intrinio provider"""
        logger.info("Initializing Intrinio provider")

        if not self.config.api_key:
            raise ProviderError("Intrinio API key not configured")

        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.config.api_key}"}
        )
        self._is_initialized = True
        logger.info("Intrinio provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Intrinio provider"""
        logger.info("Shutting down Intrinio provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to Intrinio"""
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
                    raise ProviderRateLimitError("Intrinio rate limit exceeded", retry_after=60)
                elif response.status == 401:
                    raise ProviderError("Intrinio authentication failed")
                elif response.status == 404:
                    raise ProviderError("Symbol not found")
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Intrinio"""
        logger.info(f"Fetching price for {asset.symbol} from Intrinio")

        try:
            endpoint = f"/securities/{asset.symbol}/prices/realtime"

            response_data = await self._make_request(endpoint)

            if not response_data:
                raise ProviderError(f"No price data available for {asset.symbol}")

            data = {
                "price": float(response_data.get("last_price", 0.0)),
                "bid_price": float(response_data.get("bid_price", 0.0)),
                "bid_size": int(response_data.get("bid_size", 0)),
                "ask_price": float(response_data.get("ask_price", 0.0)),
                "ask_size": int(response_data.get("ask_size", 0)),
                "open": float(response_data.get("open_price", 0.0)),
                "high": float(response_data.get("high_price", 0.0)),
                "low": float(response_data.get("low_price", 0.0)),
                "volume": int(response_data.get("volume", 0)),
                "last_time": response_data.get("last_time", ""),
                "source": response_data.get("source", ""),
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
                metadata={"source": "intrinio"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Intrinio for {asset.symbol}: {e}")
            raise ProviderError(f"Intrinio fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Intrinio"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Intrinio")

        try:
            # Map timeframe to frequency
            frequency = "daily"
            if timeframe == "1h":
                frequency = "hourly"

            endpoint = f"/securities/{asset.symbol}/prices"
            params = {
                "frequency": frequency,
                "page_size": str(min(limit, 10000)),
            }

            response_data = await self._make_request(endpoint, params)

            stock_prices = response_data.get("stock_prices", [])
            if not stock_prices:
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            for bar in stock_prices[:limit]:
                ohlcv_data.append({
                    "timestamp": bar.get("date"),
                    "open": float(bar.get("open", 0.0)),
                    "high": float(bar.get("high", 0.0)),
                    "low": float(bar.get("low", 0.0)),
                    "close": float(bar.get("close", 0.0)),
                    "volume": int(bar.get("volume", 0)),
                    "adjusted_close": float(bar.get("adj_close", 0.0)),
                    "adjusted_high": float(bar.get("adj_high", 0.0)),
                    "adjusted_low": float(bar.get("adj_low", 0.0)),
                    "adjusted_open": float(bar.get("adj_open", 0.0)),
                    "adjusted_volume": int(bar.get("adj_volume", 0)),
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
                metadata={"source": "intrinio"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Intrinio for {asset.symbol}: {e}")
            raise ProviderError(f"Intrinio OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Intrinio"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from Intrinio")

        try:
            # Get company info
            endpoint = f"/companies/{asset.symbol}"

            response_data = await self._make_request(endpoint)

            if not response_data:
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            data = {
                "symbol": response_data.get("ticker", ""),
                "name": response_data.get("name", ""),
                "lei": response_data.get("lei", ""),
                "cik": response_data.get("cik", ""),
                "exchange": response_data.get("stock_exchange", ""),
                "sic": response_data.get("sic", ""),
                "business_address": response_data.get("business_address", ""),
                "mailing_address": response_data.get("mailing_address", ""),
                "business_phone_no": response_data.get("business_phone_no", ""),
                "hq_address1": response_data.get("hq_address1", ""),
                "hq_city": response_data.get("hq_city", ""),
                "hq_state": response_data.get("hq_state", ""),
                "hq_country": response_data.get("hq_country", ""),
                "entity_legal_form": response_data.get("entity_legal_form", ""),
                "latest_filing_date": response_data.get("latest_filing_date", ""),
                "sector": response_data.get("sector", ""),
                "industry_category": response_data.get("industry_category", ""),
                "industry_group": response_data.get("industry_group", ""),
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
                metadata={"source": "intrinio"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from Intrinio for {asset.symbol}: {e}")
            raise ProviderError(f"Intrinio fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles from Intrinio"""
        logger.info(f"Fetching news for {asset.symbol} from Intrinio")

        try:
            endpoint = f"/companies/{asset.symbol}/news"
            params = {"page_size": str(limit)}

            response_data = await self._make_request(endpoint, params)

            news_items = response_data.get("news", [])

            articles = []
            for article in news_items[:limit]:
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "summary": article.get("summary", ""),
                    "published_at": article.get("publication_date", ""),
                    "company": article.get("company", {}).get("name", ""),
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
                metadata={"source": "intrinio"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news from Intrinio for {asset.symbol}: {e}")
            raise ProviderError(f"Intrinio news fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Intrinio primarily supports US equities and options
        return asset.asset_type in [AssetType.EQUITY, AssetType.OPTION, AssetType.ETF]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.99,
            avg_latency_ms=100.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
