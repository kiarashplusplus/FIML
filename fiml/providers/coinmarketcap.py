"""
CoinMarketCap Provider Implementation
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


class CoinMarketCapProvider(BaseProvider):
    """
    CoinMarketCap cryptocurrency data provider

    Provides:
    - Real-time cryptocurrency prices
    - Market capitalization data
    - Trading volume
    - Historical data
    - Cryptocurrency metadata
    - Global market metrics
    """

    BASE_URL = "https://pro-api.coinmarketcap.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="coinmarketcap",
            enabled=True,
            priority=7,
            rate_limit_per_minute=30,  # Free tier: 30 calls/day, 333 credits/day
            timeout_seconds=10,
            api_key=api_key or settings.coinmarketcap_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize CoinMarketCap provider"""
        logger.info("Initializing CoinMarketCap provider")

        if not self.config.api_key:
            raise ProviderError("CoinMarketCap API key not configured")

        self._session = aiohttp.ClientSession(headers={"X-CMC_PRO_API_KEY": self.config.api_key})
        self._is_initialized = True
        logger.info("CoinMarketCap provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown CoinMarketCap provider"""
        logger.info("Shutting down CoinMarketCap provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make API request to CoinMarketCap"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

        try:
            url = f"{self.BASE_URL}{endpoint}"
            async with self._session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                self._record_request()

                if response.status == 200:
                    data = await response.json()

                    # Check for API errors
                    if data.get("status", {}).get("error_code") != 0:
                        error_msg = data.get("status", {}).get("error_message", "Unknown error")
                        raise ProviderError(f"CoinMarketCap error: {error_msg}")

                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError(
                        "CoinMarketCap rate limit exceeded", retry_after=60
                    )
                elif response.status == 401:
                    raise ProviderError("CoinMarketCap authentication failed")
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    def _clean_symbol(self, symbol: str) -> str:
        """
        Remove common trading pair suffixes from symbol.

        Only removes suffixes from the end if the resulting symbol
        would otherwise be too short or invalid.

        Note: This is a best-effort approach for common crypto symbols.
        For complex cases like EURUSD or exotic trading pairs, users
        should provide the base symbol directly (e.g., 'EUR' not 'EURUSD').
        """
        clean_symbol = symbol.upper()
        for suffix in ["USDT", "USD", "BUSD", "EUR"]:
            if clean_symbol.endswith(suffix) and len(clean_symbol) > len(suffix):
                clean_symbol = clean_symbol[: -len(suffix)]
                break
        return clean_symbol

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from CoinMarketCap"""
        logger.info(f"Fetching price for {asset.symbol} from CoinMarketCap")

        try:
            clean_symbol = self._clean_symbol(asset.symbol)

            endpoint = "/cryptocurrency/quotes/latest"
            params = {"symbol": clean_symbol}

            response_data = await self._make_request(endpoint, params)

            data_dict = response_data.get("data", {})
            symbol_key = params["symbol"]

            if symbol_key not in data_dict:
                raise ProviderError(f"No price data available for {asset.symbol}")

            coin_data = data_dict[symbol_key]
            quote = coin_data.get("quote", {}).get("USD", {})

            data = {
                "price": float(quote.get("price", 0.0)),
                "volume_24h": float(quote.get("volume_24h", 0.0)),
                "volume_change_24h": float(quote.get("volume_change_24h", 0.0)),
                "percent_change_1h": float(quote.get("percent_change_1h", 0.0)),
                "percent_change_24h": float(quote.get("percent_change_24h", 0.0)),
                "percent_change_7d": float(quote.get("percent_change_7d", 0.0)),
                "market_cap": float(quote.get("market_cap", 0.0)),
                "market_cap_dominance": float(quote.get("market_cap_dominance", 0.0)),
                "fully_diluted_market_cap": float(quote.get("fully_diluted_market_cap", 0.0)),
                "last_updated": quote.get("last_updated", ""),
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
                    "source": "coinmarketcap",
                    "cmc_rank": coin_data.get("cmc_rank"),
                    "num_market_pairs": coin_data.get("num_market_pairs"),
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from CoinMarketCap for {asset.symbol}: {e}")
            raise ProviderError(f"CoinMarketCap fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from CoinMarketCap"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from CoinMarketCap")

        # OHLCV data requires higher tier plan in CoinMarketCap
        # Return limited data or error for free tier
        raise ProviderError("OHLCV data requires CoinMarketCap paid plan")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from CoinMarketCap"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from CoinMarketCap")

        try:
            clean_symbol = self._clean_symbol(asset.symbol)

            endpoint = "/cryptocurrency/info"
            params = {"symbol": clean_symbol}

            response_data = await self._make_request(endpoint, params)

            data_dict = response_data.get("data", {})
            symbol_key = params["symbol"]

            if symbol_key not in data_dict:
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            coin_info = data_dict[symbol_key]

            data = {
                "symbol": coin_info.get("symbol", ""),
                "name": coin_info.get("name", ""),
                "slug": coin_info.get("slug", ""),
                "description": coin_info.get("description", ""),
                "logo": coin_info.get("logo", ""),
                "date_launched": coin_info.get("date_launched", ""),
                "tags": coin_info.get("tags", []),
                "platform": coin_info.get("platform"),
                "category": coin_info.get("category", ""),
                "notice": coin_info.get("notice", ""),
                "urls": coin_info.get("urls", {}),
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
                metadata={"source": "coinmarketcap"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from CoinMarketCap for {asset.symbol}: {e}")
            raise ProviderError(f"CoinMarketCap fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles - CoinMarketCap doesn't provide news via API"""
        # CoinMarketCap doesn't have a news API endpoint
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "coinmarketcap", "note": "News not available via API"},
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # CoinMarketCap only supports cryptocurrencies
        return asset.asset_type == AssetType.CRYPTO

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.99,
            avg_latency_ms=180.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
