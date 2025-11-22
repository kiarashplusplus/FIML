"""
Alpha Vantage Provider Implementation
"""

from datetime import datetime, timezone
from typing import Dict, Optional, Any
import asyncio

import aiohttp

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderTimeoutError, ProviderRateLimitError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)


class AlphaVantageProvider(BaseProvider):
    """
    Alpha Vantage data provider
    
    Provides:
    - Real-time and historical equity data
    - Fundamental data (earnings, financial statements)
    - Technical indicators
    - Free tier: 5 API requests per minute, 500 requests per day
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="alpha_vantage",
            enabled=True,
            priority=7,
            rate_limit_per_minute=5,  # Free tier limit
            timeout_seconds=10,
            api_key=api_key or settings.alpha_vantage_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_timestamps: list = []

    async def initialize(self) -> None:
        """Initialize Alpha Vantage provider"""
        logger.info("Initializing Alpha Vantage provider")
        
        if not self.config.api_key:
            raise ProviderError("Alpha Vantage API key not configured")
        
        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("Alpha Vantage provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Alpha Vantage provider"""
        logger.info("Shutting down Alpha Vantage provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limits"""
        now = datetime.now(timezone.utc)
        
        # Remove timestamps older than 1 minute
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if (now - ts).total_seconds() < 60
        ]
        
        # Check if we've exceeded the rate limit
        if len(self._request_timestamps) >= self.config.rate_limit_per_minute:
            wait_time = 60 - (now - self._request_timestamps[0]).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                raise ProviderRateLimitError(
                    f"Rate limit exceeded. Wait {wait_time:.1f}s",
                    retry_after=int(wait_time) + 1
                )

    async def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make API request to Alpha Vantage"""
        if not self._session:
            raise ProviderError("Provider not initialized")
        
        await self._check_rate_limit()
        
        params["apikey"] = self.config.api_key
        
        try:
            async with self._session.get(
                self.BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                self._request_timestamps.append(datetime.now(timezone.utc))
                self._record_request()
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for API errors
                    if "Error Message" in data:
                        raise ProviderError(f"Alpha Vantage error: {data['Error Message']}")
                    
                    if "Note" in data:
                        # Rate limit message
                        raise ProviderRateLimitError(
                            "Alpha Vantage rate limit exceeded",
                            retry_after=60
                        )
                    
                    return data
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")
                    
        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from Alpha Vantage"""
        logger.info(f"Fetching price for {asset.symbol} from Alpha Vantage")
        
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": asset.symbol,
            }
            
            response_data = await self._make_request(params)
            
            quote = response_data.get("Global Quote", {})
            
            if not quote:
                raise ProviderError(f"No quote data available for {asset.symbol}")
            
            data = {
                "price": float(quote.get("05. price", 0.0)),
                "change": float(quote.get("09. change", 0.0)),
                "change_percent": float(quote.get("10. change percent", "0").rstrip("%")),
                "volume": int(quote.get("06. volume", 0)),
                "previous_close": float(quote.get("08. previous close", 0.0)),
                "open": float(quote.get("02. open", 0.0)),
                "high": float(quote.get("03. high", 0.0)),
                "low": float(quote.get("04. low", 0.0)),
                "latest_trading_day": quote.get("07. latest trading day", ""),
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
                metadata={
                    "source": "alpha_vantage",
                    "function": "GLOBAL_QUOTE",
                },
            )
            
        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from Alpha Vantage for {asset.symbol}: {e}")
            raise ProviderError(f"Alpha Vantage fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from Alpha Vantage"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from Alpha Vantage")
        
        try:
            # Map timeframe to Alpha Vantage function
            if timeframe == "1d":
                function = "TIME_SERIES_DAILY"
                outputsize = "compact" if limit <= 100 else "full"
            elif timeframe in ["1h", "60min"]:
                function = "TIME_SERIES_INTRADAY"
                outputsize = "compact"
            else:
                function = "TIME_SERIES_DAILY"
                outputsize = "compact"
            
            params = {
                "function": function,
                "symbol": asset.symbol,
                "outputsize": outputsize,
            }
            
            if function == "TIME_SERIES_INTRADAY":
                params["interval"] = "60min"
            
            response_data = await self._make_request(params)
            
            # Extract time series data
            time_series_key = None
            for key in response_data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break
            
            if not time_series_key:
                raise ProviderError(f"No time series data available for {asset.symbol}")
            
            time_series = response_data[time_series_key]
            
            # Convert to standard format
            ohlcv_data = []
            for timestamp, values in list(time_series.items())[:limit]:
                ohlcv_data.append({
                    "timestamp": timestamp,
                    "open": float(values.get("1. open", 0.0)),
                    "high": float(values.get("2. high", 0.0)),
                    "low": float(values.get("3. low", 0.0)),
                    "close": float(values.get("4. close", 0.0)),
                    "volume": int(values.get("5. volume", 0)),
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
                metadata={
                    "source": "alpha_vantage",
                    "function": function,
                },
            )
            
        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from Alpha Vantage for {asset.symbol}: {e}")
            raise ProviderError(f"Alpha Vantage OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from Alpha Vantage"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from Alpha Vantage")
        
        try:
            params = {
                "function": "OVERVIEW",
                "symbol": asset.symbol,
            }
            
            response_data = await self._make_request(params)
            
            if not response_data or "Symbol" not in response_data:
                raise ProviderError(f"No fundamental data available for {asset.symbol}")
            
            # Extract key fundamentals
            data = {
                "symbol": response_data.get("Symbol", ""),
                "name": response_data.get("Name", ""),
                "description": response_data.get("Description", ""),
                "exchange": response_data.get("Exchange", ""),
                "currency": response_data.get("Currency", ""),
                "country": response_data.get("Country", ""),
                "sector": response_data.get("Sector", ""),
                "industry": response_data.get("Industry", ""),
                "market_cap": int(response_data.get("MarketCapitalization", 0)),
                "pe_ratio": float(response_data.get("PERatio", 0.0) or 0.0),
                "peg_ratio": float(response_data.get("PEGRatio", 0.0) or 0.0),
                "book_value": float(response_data.get("BookValue", 0.0) or 0.0),
                "dividend_per_share": float(response_data.get("DividendPerShare", 0.0) or 0.0),
                "dividend_yield": float(response_data.get("DividendYield", 0.0) or 0.0),
                "eps": float(response_data.get("EPS", 0.0) or 0.0),
                "revenue_per_share": float(response_data.get("RevenuePerShareTTM", 0.0) or 0.0),
                "profit_margin": float(response_data.get("ProfitMargin", 0.0) or 0.0),
                "operating_margin": float(response_data.get("OperatingMarginTTM", 0.0) or 0.0),
                "roe": float(response_data.get("ReturnOnEquityTTM", 0.0) or 0.0),
                "roa": float(response_data.get("ReturnOnAssetsTTM", 0.0) or 0.0),
                "revenue_ttm": int(response_data.get("RevenueTTM", 0)),
                "gross_profit_ttm": int(response_data.get("GrossProfitTTM", 0)),
                "ebitda": int(response_data.get("EBITDA", 0)),
                "52_week_high": float(response_data.get("52WeekHigh", 0.0) or 0.0),
                "52_week_low": float(response_data.get("52WeekLow", 0.0) or 0.0),
                "50_day_ma": float(response_data.get("50DayMovingAverage", 0.0) or 0.0),
                "200_day_ma": float(response_data.get("200DayMovingAverage", 0.0) or 0.0),
                "shares_outstanding": int(response_data.get("SharesOutstanding", 0)),
                "beta": float(response_data.get("Beta", 0.0) or 0.0),
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
                metadata={
                    "source": "alpha_vantage",
                    "function": "OVERVIEW",
                },
            )
            
        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from Alpha Vantage for {asset.symbol}: {e}")
            raise ProviderError(f"Alpha Vantage fundamentals fetch failed: {e}")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles from Alpha Vantage"""
        logger.info(f"Fetching news for {asset.symbol} from Alpha Vantage")
        
        try:
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": asset.symbol,
                "limit": str(limit),
            }
            
            response_data = await self._make_request(params)
            
            feed = response_data.get("feed", [])
            
            articles = []
            for article in feed[:limit]:
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("time_published", ""),
                    "source": article.get("source", ""),
                    "summary": article.get("summary", ""),
                    "sentiment": float(article.get("overall_sentiment_score", 0.0)),
                })
            
            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.NEWS,
                data={"articles": articles},
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.90,
                metadata={
                    "source": "alpha_vantage",
                    "function": "NEWS_SENTIMENT",
                },
            )
            
        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news from Alpha Vantage for {asset.symbol}: {e}")
            raise ProviderError(f"Alpha Vantage news fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        # Alpha Vantage primarily supports equities and some forex
        return asset.asset_type in [AssetType.EQUITY, AssetType.FOREX]

    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        try:
            # Simple health check - fetch a known symbol
            test_asset = Asset(symbol="IBM", asset_type=AssetType.EQUITY)
            await self.fetch_price(test_asset)
            
            return ProviderHealth(
                provider_name=self.name,
                is_healthy=True,
                uptime_percent=0.99,
                avg_latency_ms=100.0,
                success_rate=1.0 - (self._error_count / max(self._request_count, 1)),
                last_check=datetime.now(timezone.utc),
                error_count_24h=self._error_count,
            )
        except Exception as e:
            logger.error(f"Alpha Vantage health check failed: {e}")
            return ProviderHealth(
                provider_name=self.name,
                is_healthy=False,
                uptime_percent=0.0,
                avg_latency_ms=0.0,
                success_rate=0.0,
                last_check=datetime.now(timezone.utc),
                error_count_24h=self._error_count,
            )

    def _record_request(self) -> None:
        """Record a successful request"""
        self._request_count += 1
        self._last_request_time = datetime.now(timezone.utc)

    def _record_error(self) -> None:
        """Record an error"""
        self._error_count += 1
