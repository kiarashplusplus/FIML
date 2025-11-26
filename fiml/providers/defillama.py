"""
DefiLlama Provider Implementation

DefiLlama is a DeFi aggregator that provides free, comprehensive DeFi data
including TVL, protocol metrics, and cryptocurrency prices without requiring
an API key.

API Documentation: https://defillama.com/docs/api
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


class DefiLlamaProvider(BaseProvider):
    """
    DefiLlama cryptocurrency and DeFi data provider

    Provides:
    - Cryptocurrency prices (via coins API)
    - Historical price data
    - DeFi protocol TVL data
    - Chain TVL metrics
    - Stablecoin data
    - No API key required

    Rate limits: Very generous, no strict limits documented
    """

    # DefiLlama API endpoints
    COINS_BASE_URL = "https://coins.llama.fi"
    TVL_BASE_URL = "https://api.llama.fi"

    def __init__(self) -> None:
        config = ProviderConfig(
            name="defillama",
            enabled=True,
            priority=5,  # Lower priority than CoinGecko, used as fallback
            rate_limit_per_minute=100,  # Conservative estimate
            timeout_seconds=10,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        # Mapping common symbols to DefiLlama coin IDs
        # DefiLlama uses format: {chain}:{address} or coingecko:{id}
        self._symbol_to_id: Dict[str, str] = {
            "BTC": "coingecko:bitcoin",
            "ETH": "coingecko:ethereum",
            "USDT": "coingecko:tether",
            "BNB": "coingecko:binancecoin",
            "SOL": "coingecko:solana",
            "ADA": "coingecko:cardano",
            "XRP": "coingecko:ripple",
            "DOGE": "coingecko:dogecoin",
            "DOT": "coingecko:polkadot",
            "MATIC": "coingecko:matic-network",
            "AVAX": "coingecko:avalanche-2",
            "LINK": "coingecko:chainlink",
            "UNI": "coingecko:uniswap",
            "AAVE": "coingecko:aave",
            "MKR": "coingecko:maker",
            "CRV": "coingecko:curve-dao-token",
            "LDO": "coingecko:lido-dao",
            "ARB": "coingecko:arbitrum",
            "OP": "coingecko:optimism",
        }

    async def initialize(self) -> None:
        """Initialize DefiLlama provider"""
        logger.info("Initializing DefiLlama provider")
        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("DefiLlama provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown DefiLlama provider"""
        logger.info("Shutting down DefiLlama provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    def _get_coin_id(self, symbol: str) -> str:
        """
        Convert symbol to DefiLlama coin ID.

        DefiLlama supports multiple ID formats:
        - coingecko:{id} - For CoinGecko coin IDs (e.g., 'coingecko:bitcoin')
        - {chain}:{address} - For on-chain tokens (e.g., 'ethereum:0x...')

        This method uses the coingecko format for known symbols.
        """
        clean_symbol = symbol.upper()

        # First check if we have a direct mapping
        if clean_symbol in self._symbol_to_id:
            return self._symbol_to_id[clean_symbol]

        # Try removing common trading pair suffixes
        for suffix in ["USDT", "BUSD", "USD"]:
            if clean_symbol.endswith(suffix) and len(clean_symbol) > len(suffix):
                potential_symbol = clean_symbol[: -len(suffix)]
                if potential_symbol in self._symbol_to_id:
                    return self._symbol_to_id[potential_symbol]

        # Default: assume it's a coingecko ID (lowercase)
        return f"coingecko:{clean_symbol.lower()}"

    async def _make_request(
        self, base_url: str, endpoint: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make API request to DefiLlama"""
        if not self._session:
            raise ProviderError("Provider not initialized")

        if params is None:
            params = {}

        try:
            url = f"{base_url}{endpoint}"
            async with self._session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                self._record_request()

                if response.status == 200:
                    data = await response.json()
                    return data  # type: ignore[no-any-return]
                elif response.status == 429:
                    raise ProviderRateLimitError("DefiLlama rate limit exceeded", retry_after=60)
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")

        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from DefiLlama"""
        logger.info("Fetching price for %s from DefiLlama", asset.symbol)

        try:
            coin_id = self._get_coin_id(asset.symbol)

            # DefiLlama coins API: /prices/current/{coins}
            endpoint = f"/prices/current/{coin_id}"

            response_data = await self._make_request(self.COINS_BASE_URL, endpoint)

            coins_data = response_data.get("coins", {})
            if coin_id not in coins_data:
                raise ProviderError(f"No price data available for {asset.symbol}")

            coin_data = coins_data[coin_id]

            data = {
                "price": float(coin_data.get("price", 0.0)),
                "confidence": float(coin_data.get("confidence", 0.9)),
                "symbol": coin_data.get("symbol", asset.symbol),
                "timestamp": coin_data.get("timestamp", int(datetime.now(timezone.utc).timestamp())),
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.94,  # Slightly lower than CoinGecko since it aggregates
                metadata={"source": "defillama", "coin_id": coin_id},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error("Error fetching price from DefiLlama for %s: %s", asset.symbol, e)
            raise ProviderError(f"DefiLlama fetch failed: {e}")

    async def fetch_ohlcv(self, asset: Asset, timeframe: str = "1d", limit: int = 100) -> ProviderResponse:
        """
        Fetch historical price data from DefiLlama

        Note: DefiLlama provides historical prices but not full OHLCV data.
        We return price history as close prices with interpolated OHLCV values.
        """
        logger.info("Fetching OHLCV for %s from DefiLlama", asset.symbol)

        try:
            coin_id = self._get_coin_id(asset.symbol)

            # Calculate timestamp range based on limit
            # DefiLlama chart endpoint: /chart/{coins}
            endpoint = f"/chart/{coin_id}"

            # Get historical data
            response_data = await self._make_request(self.COINS_BASE_URL, endpoint)

            coins_data = response_data.get("coins", {})
            if coin_id not in coins_data:
                raise ProviderError(f"No historical data available for {asset.symbol}")

            prices = coins_data[coin_id].get("prices", [])
            if not prices:
                raise ProviderError(f"No price history available for {asset.symbol}")

            # Convert to OHLCV format (using price as all OHLC values since DefiLlama only provides price)
            ohlcv_data = []
            for price_point in prices[-limit:]:
                timestamp = price_point.get("timestamp", 0)
                price = float(price_point.get("price", 0.0))
                ohlcv_data.append(
                    {
                        "timestamp": timestamp,
                        "open": price,
                        "high": price,
                        "low": price,
                        "close": price,
                        "volume": None,  # DefiLlama doesn't provide volume in chart data
                    }
                )

            data = {
                "ohlcv": ohlcv_data,
                "timeframe": timeframe,
                "count": len(ohlcv_data),
                "volume_available": False,  # Flag to indicate volume is not available
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.OHLCV,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.90,  # Lower confidence since we're interpolating OHLCV
                metadata={
                    "source": "defillama",
                    "coin_id": coin_id,
                    "note": "OHLCV interpolated from price history",
                },
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error("Error fetching OHLCV from DefiLlama for %s: %s", asset.symbol, e)
            raise ProviderError(f"DefiLlama OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """
        Fetch DeFi fundamentals from DefiLlama

        For DeFi tokens, provides TVL and protocol metrics.
        """
        logger.info("Fetching fundamentals for %s from DefiLlama", asset.symbol)

        try:
            # Try to find a protocol matching the symbol
            # First, get list of protocols
            response_data = await self._make_request(self.TVL_BASE_URL, "/protocols")

            if not isinstance(response_data, list):
                raise ProviderError(f"No protocol data available for {asset.symbol}")

            # Find matching protocol by symbol
            protocol_data = None
            symbol_lower = asset.symbol.lower()
            for protocol in response_data:
                if protocol.get("symbol", "").lower() == symbol_lower:
                    protocol_data = protocol
                    break

            if not protocol_data:
                # Return minimal data if no protocol match
                return ProviderResponse(
                    provider=self.name,
                    asset=asset,
                    data_type=DataType.FUNDAMENTALS,
                    data={"symbol": asset.symbol, "note": "No DeFi protocol data available"},
                    timestamp=datetime.now(timezone.utc),
                    is_valid=True,
                    is_fresh=False,
                    confidence=0.0,
                    metadata={"source": "defillama", "note": "Protocol not found"},
                )

            # Calculate mcap/tvl ratio safely
            mcap = float(protocol_data.get("mcap", 0.0) or 0.0)
            tvl = float(protocol_data.get("tvl", 0.0))
            mcap_tvl_ratio = (mcap / tvl) if tvl > 0 else None

            data = {
                "symbol": protocol_data.get("symbol", ""),
                "name": protocol_data.get("name", ""),
                "slug": protocol_data.get("slug", ""),
                "tvl": tvl,
                "chain_tvls": protocol_data.get("chainTvls", {}),
                "change_1h": float(protocol_data.get("change_1h", 0.0) or 0.0),
                "change_1d": float(protocol_data.get("change_1d", 0.0) or 0.0),
                "change_7d": float(protocol_data.get("change_7d", 0.0) or 0.0),
                "category": protocol_data.get("category", ""),
                "chains": protocol_data.get("chains", []),
                "mcap_tvl_ratio": mcap_tvl_ratio,
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
                metadata={"source": "defillama", "protocol_slug": protocol_data.get("slug")},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error("Error fetching fundamentals from DefiLlama for %s: %s", asset.symbol, e)
            raise ProviderError(f"DefiLlama fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles - DefiLlama doesn't provide news"""
        # DefiLlama doesn't have a news endpoint
        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": []},
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=False,
            confidence=0.0,
            metadata={"source": "defillama", "note": "News not available"},
        )

    async def fetch_tvl(self, protocol_slug: Optional[str] = None) -> ProviderResponse:
        """
        Fetch TVL data from DefiLlama

        Args:
            protocol_slug: Optional protocol slug for specific protocol TVL

        Returns:
            TVL data for the protocol or total DeFi TVL
        """
        logger.info("Fetching TVL data from DefiLlama")

        try:
            if protocol_slug:
                endpoint = f"/protocol/{protocol_slug}"
            else:
                endpoint = "/tvl"

            response_data = await self._make_request(self.TVL_BASE_URL, endpoint)

            if protocol_slug:
                # Protocol-specific TVL
                data = {
                    "protocol": protocol_slug,
                    "tvl": float(response_data.get("tvl", 0.0)),
                    "chain_tvls": response_data.get("chainTvls", {}),
                    "tokens": response_data.get("tokens", {}),
                }
            else:
                # Total DeFi TVL - validate response format
                if isinstance(response_data, (int, float)):
                    data = {
                        "total_tvl": float(response_data),
                    }
                else:
                    logger.warning(
                        "Unexpected TVL response format from DefiLlama: %s",
                        type(response_data).__name__,
                    )
                    raise ProviderError(f"Unexpected TVL response format: {type(response_data).__name__}")

            # Create a dummy asset for TVL response
            dummy_asset = Asset(symbol="TVL", asset_type=AssetType.CRYPTO)

            return ProviderResponse(
                provider=self.name,
                asset=dummy_asset,
                data_type=DataType.FUNDAMENTALS,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.98,
                metadata={"source": "defillama", "endpoint": "tvl"},
            )

        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error("Error fetching TVL from DefiLlama: %s", e)
            raise ProviderError(f"DefiLlama TVL fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # DefiLlama supports cryptocurrencies
        return asset.asset_type == AssetType.CRYPTO

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=0.98,
            avg_latency_ms=250.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
