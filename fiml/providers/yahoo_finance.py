"""
Yahoo Finance Provider Implementation
"""

from datetime import datetime, timezone

import yfinance as yf

from fiml.core.exceptions import ProviderError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)


class YahooFinanceProvider(BaseProvider):
    """
    Yahoo Finance data provider

    Free, reliable source for equity and ETF data
    """

    def __init__(self):
        config = ProviderConfig(
            name="yahoo_finance",
            enabled=True,
            priority=5,
            rate_limit_per_minute=2000,  # Very permissive
            timeout_seconds=10,
        )
        super().__init__(config)
        self._cache: dict = {}

    async def initialize(self) -> None:
        """Initialize Yahoo Finance provider"""
        logger.info("Initializing Yahoo Finance provider")
        self._is_initialized = True

    async def shutdown(self) -> None:
        """Shutdown Yahoo Finance provider"""
        logger.info("Shutting down Yahoo Finance provider")
        self._cache.clear()
        self._is_initialized = False

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Yahoo Finance"""
        self._record_request()

        try:
            ticker = yf.Ticker(asset.symbol)
            info = ticker.info

            if not info or "currentPrice" not in info:
                raise ProviderError(f"No price data available for {asset.symbol}")

            data = {
                "price": info.get("currentPrice", 0.0),
                "change": info.get("regularMarketChange", 0.0),
                "change_percent": info.get("regularMarketChangePercent", 0.0),
                "volume": info.get("volume", 0),
                "market_cap": info.get("marketCap", 0),
                "previous_close": info.get("previousClose", 0.0),
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
                metadata={"source": "yahoo_finance"},
            )

        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Yahoo Finance for {asset.symbol}: {e}")
            raise ProviderError(f"Yahoo Finance fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Yahoo Finance"""
        self._record_request()

        try:
            ticker = yf.Ticker(asset.symbol)

            # Map timeframe to yfinance period
            period_map = {
                "1d": f"{limit}d",
                "1h": f"{limit}h",
                "5m": f"{min(limit, 60)}d",  # Max 60 days for intraday
            }
            period = period_map.get(timeframe, f"{limit}d")

            history = ticker.history(period=period, interval=timeframe)

            if history.empty:
                raise ProviderError(f"No OHLCV data available for {asset.symbol}")

            candles = []
            for idx, row in history.iterrows():
                candles.append(
                    {
                        "timestamp": idx,
                        "open": row["Open"],
                        "high": row["High"],
                        "low": row["Low"],
                        "close": row["Close"],
                        "volume": row["Volume"],
                    }
                )

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.OHLCV,
                data={"candles": candles, "timeframe": timeframe},
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.95,
            )

        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Yahoo Finance for {asset.symbol}: {e}")
            raise ProviderError(f"Yahoo Finance OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Yahoo Finance"""
        self._record_request()

        try:
            ticker = yf.Ticker(asset.symbol)
            info = ticker.info

            if not info:
                raise ProviderError(f"No fundamental data available for {asset.symbol}")

            data = {
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "eps": info.get("trailingEps"),
                "beta": info.get("beta"),
                "dividend_yield": info.get("dividendYield"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "full_time_employees": info.get("fullTimeEmployees"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
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
            )

        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from Yahoo Finance for {asset.symbol}: {e}")
            raise ProviderError(f"Yahoo Finance fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news from Yahoo Finance"""
        self._record_request()

        try:
            ticker = yf.Ticker(asset.symbol)
            news = ticker.news[:limit] if ticker.news else []

            articles = []
            for article in news:
                articles.append(
                    {
                        "title": article.get("title"),
                        "url": article.get("link"),
                        "publisher": article.get("publisher"),
                        "published_at": datetime.fromtimestamp(article.get("providerPublishTime", 0)),
                        "type": article.get("type"),
                    }
                )

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.NEWS,
                data={"articles": articles},
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.85,
            )

        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news from Yahoo Finance for {asset.symbol}: {e}")
            raise ProviderError(f"Yahoo Finance news fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if Yahoo Finance supports this asset"""
        # Yahoo Finance primarily supports equities and ETFs
        supported_types = [AssetType.EQUITY, AssetType.ETF, AssetType.INDEX]
        return asset.asset_type in supported_types

    async def get_health(self) -> ProviderHealth:
        """Get Yahoo Finance provider health"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=await self.get_uptime_24h(),
            avg_latency_ms=150.0,  # Yahoo Finance is generally fast
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
