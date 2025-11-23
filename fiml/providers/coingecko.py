"""
CoinGecko Provider Implementation
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp

from fiml.core.exceptions import ProviderError, ProviderRateLimitError, ProviderTimeoutError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)


class CoinGeckoProvider(BaseProvider):
    """
    CoinGecko cryptocurrency data provider

    Provides:
    - Real-time cryptocurrency prices
    - Historical price data
    - Market data (volume, market cap, etc.)
    - Coin metadata
    - No API key required for public endpoints
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        config = ProviderConfig(
            name="coingecko",
            enabled=True,
            priority=6,
            rate_limit_per_minute=50,  # Free tier: 50 calls/minute
            timeout_seconds=10,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        # Mapping common symbols to CoinGecko IDs
        self._symbol_to_id = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "USDT": "tether",
            "BNB": "binancecoin",
            "SOL": "solana",
            "ADA": "cardano",
            "XRP": "ripple",
            "DOGE": "dogecoin",
            "DOT": "polkadot",
            "MATIC": "matic-network",
        }

    async def initialize(self) -> None:
        """Initialize CoinGecko provider"""
        logger.info("Initializing CoinGecko provider")
        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("CoinGecko provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown CoinGecko provider"""
        logger.info("Shutting down CoinGecko provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    def _get_coin_id(self, symbol: str) -> str:
        """Convert symbol to CoinGecko coin ID"""
        clean_symbol = symbol.upper()
        
        # First check if we have a direct mapping for the full symbol
        if clean_symbol in self._symbol_to_id:
            return self._symbol_to_id[clean_symbol]
        
        # Try removing common trading pair suffixes (only at the end)
        # Only remove if the resulting symbol has a known mapping
        for suffix in ["USDT", "BUSD", "USD"]:  # More conservative list, removed BTC/ETH
            if clean_symbol.endswith(suffix) and len(clean_symbol) > len(suffix):
                potential_symbol = clean_symbol[:-len(suffix)]
                if potential_symbol in self._symbol_to_id:
                    return self._symbol_to_id[potential_symbol]
        
        # If no mapping found, return lowercase as coin ID (API will handle it)
        return clean_symbol.lower()

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to CoinGecko"""
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
                    raise ProviderRateLimitError("CoinGecko rate limit exceeded", retry_after=60)
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from CoinGecko"""
        logger.info(f"Fetching price for {asset.symbol} from CoinGecko")

        try:
            coin_id = self._get_coin_id(asset.symbol)
            
            endpoint = "/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
            }
            
            response_data = await self._make_request(endpoint, params)

            if coin_id not in response_data:
                raise ProviderError(f"No price data available for {asset.symbol}")

            coin_data = response_data[coin_id]
            
            data = {
                "price": float(coin_data.get("usd", 0.0)),
                "market_cap": float(coin_data.get("usd_market_cap", 0.0)),
                "volume_24h": float(coin_data.get("usd_24h_vol", 0.0)),
                "change_24h": float(coin_data.get("usd_24h_change", 0.0)),
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
                metadata={"source": "coingecko", "coin_id": coin_id},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from CoinGecko for {asset.symbol}: {e}")
            raise ProviderError(f"CoinGecko fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from CoinGecko"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from CoinGecko")

        try:
            coin_id = self._get_coin_id(asset.symbol)
            
            # CoinGecko uses days for historical data
            days = min(limit, 365) if timeframe == "1d" else 30
            
            endpoint = f"/coins/{coin_id}/ohlc"
            params = {
                "vs_currency": "usd",
                "days": str(days),
            }
            
            response_data = await self._make_request(endpoint, params)

            if not isinstance(response_data, list):
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            ohlcv_data = []
            for bar in response_data[:limit]:
                ohlcv_data.append({
                    "timestamp": bar[0],  # Timestamp in ms
                    "open": float(bar[1]),
                    "high": float(bar[2]),
                    "low": float(bar[3]),
                    "close": float(bar[4]),
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
                metadata={"source": "coingecko", "coin_id": coin_id},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from CoinGecko for {asset.symbol}: {e}")
            raise ProviderError(f"CoinGecko OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from CoinGecko"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from CoinGecko")

        try:
            coin_id = self._get_coin_id(asset.symbol)
            
            endpoint = f"/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "true",
            }
            
            response_data = await self._make_request(endpoint, params)

            if not response_data or "id" not in response_data:
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            market_data = response_data.get("market_data", {})
            
            data = {
                "symbol": response_data.get("symbol", "").upper(),
                "name": response_data.get("name", ""),
                "description": response_data.get("description", {}).get("en", ""),
                "genesis_date": response_data.get("genesis_date", ""),
                "market_cap_rank": response_data.get("market_cap_rank"),
                "market_cap": market_data.get("market_cap", {}).get("usd"),
                "total_volume": market_data.get("total_volume", {}).get("usd"),
                "current_price": market_data.get("current_price", {}).get("usd"),
                "ath": market_data.get("ath", {}).get("usd"),
                "atl": market_data.get("atl", {}).get("usd"),
                "circulating_supply": market_data.get("circulating_supply"),
                "total_supply": market_data.get("total_supply"),
                "max_supply": market_data.get("max_supply"),
                "homepage": response_data.get("links", {}).get("homepage", [""])[0],
                "blockchain_site": response_data.get("links", {}).get("blockchain_site", []),
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
                metadata={"source": "coingecko", "coin_id": coin_id},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from CoinGecko for {asset.symbol}: {e}")
            raise ProviderError(f"CoinGecko fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles - CoinGecko doesn't provide news"""
        # CoinGecko doesn't have a news endpoint
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "coingecko", "note": "News not available"},
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # CoinGecko only supports cryptocurrencies
        return asset.asset_type == AssetType.CRYPTO

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
