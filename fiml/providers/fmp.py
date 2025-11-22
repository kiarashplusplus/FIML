"""
Financial Modeling Prep (FMP) Provider Implementation
"""

from datetime import datetime
from typing import Dict, Optional, Any, List
import asyncio

import aiohttp

from fiml.core.config import settings
from fiml.core.exceptions import ProviderError, ProviderTimeoutError, ProviderRateLimitError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)


class FMPProvider(BaseProvider):
    """
    Financial Modeling Prep (FMP) data provider
    
    Provides:
    - Real-time and historical equity data
    - Financial statements (income, balance sheet, cash flow)
    - Company profiles and metrics
    - Market data and news
    - Free tier: 250 API requests per day
    """

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        config = ProviderConfig(
            name="fmp",
            enabled=True,
            priority=6,
            rate_limit_per_minute=10,  # Conservative limit
            timeout_seconds=10,
            api_key=api_key or settings.fmp_api_key,
        )
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_timestamps: list = []

    async def initialize(self) -> None:
        """Initialize FMP provider"""
        logger.info("Initializing FMP provider")
        
        if not self.config.api_key:
            raise ProviderError("FMP API key not configured")
        
        self._session = aiohttp.ClientSession()
        self._is_initialized = True
        logger.info("FMP provider initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown FMP provider"""
        logger.info("Shutting down FMP provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limits"""
        now = datetime.utcnow()
        
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

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Any:
        """Make API request to FMP"""
        if not self._session:
            raise ProviderError("Provider not initialized")
        
        await self._check_rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        if params is None:
            params = {}
        
        params["apikey"] = self.config.api_key
        
        try:
            async with self._session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                self._request_timestamps.append(datetime.utcnow())
                self._record_request()
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for API errors
                    if isinstance(data, dict) and "Error Message" in data:
                        raise ProviderError(f"FMP error: {data['Error Message']}")
                    
                    return data
                elif response.status == 429:
                    raise ProviderRateLimitError(
                        "FMP rate limit exceeded",
                        retry_after=60
                    )
                else:
                    raise ProviderError(f"HTTP {response.status}: {await response.text()}")
                    
        except asyncio.TimeoutError:
            self._record_error()
            raise ProviderTimeoutError(f"Request timeout after {self.config.timeout_seconds}s")
        except aiohttp.ClientError as e:
            self._record_error()
            raise ProviderError(f"Request failed: {e}")

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price from FMP"""
        logger.info(f"Fetching price for {asset.symbol} from FMP")
        
        try:
            endpoint = f"quote/{asset.symbol}"
            response_data = await self._make_request(endpoint)
            
            if not response_data or len(response_data) == 0:
                raise ProviderError(f"No quote data available for {asset.symbol}")
            
            quote = response_data[0]
            
            data = {
                "price": float(quote.get("price", 0.0)),
                "change": float(quote.get("change", 0.0)),
                "change_percent": float(quote.get("changesPercentage", 0.0)),
                "volume": int(quote.get("volume", 0)),
                "previous_close": float(quote.get("previousClose", 0.0)),
                "open": float(quote.get("open", 0.0)),
                "high": float(quote.get("dayHigh", 0.0)),
                "low": float(quote.get("dayLow", 0.0)),
                "market_cap": int(quote.get("marketCap", 0)),
                "pe_ratio": float(quote.get("pe", 0.0) or 0.0),
                "eps": float(quote.get("eps", 0.0) or 0.0),
                "shares_outstanding": int(quote.get("sharesOutstanding", 0)),
                "timestamp": quote.get("timestamp", 0),
            }
            
            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.PRICE,
                data=data,
                timestamp=datetime.utcnow(),
                is_valid=True,
                is_fresh=True,
                confidence=0.97,
                metadata={
                    "source": "fmp",
                    "endpoint": "quote",
                },
            )
            
        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching price from FMP for {asset.symbol}: {e}")
            raise ProviderError(f"FMP fetch failed: {e}")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV data from FMP"""
        logger.info(f"Fetching OHLCV for {asset.symbol} from FMP")
        
        try:
            endpoint = f"historical-price-full/{asset.symbol}"
            params = {}
            
            if timeframe == "1d":
                # Daily data
                pass
            elif timeframe in ["1h", "60min"]:
                # For intraday, use different endpoint
                endpoint = f"historical-chart/1hour/{asset.symbol}"
            elif timeframe == "5min":
                endpoint = f"historical-chart/5min/{asset.symbol}"
            
            response_data = await self._make_request(endpoint, params)
            
            # Extract historical data
            historical = []
            if "historical" in response_data:
                historical = response_data["historical"][:limit]
            elif isinstance(response_data, list):
                historical = response_data[:limit]
            
            if not historical:
                raise ProviderError(f"No historical data available for {asset.symbol}")
            
            # Convert to standard format
            ohlcv_data = []
            for candle in historical:
                ohlcv_data.append({
                    "timestamp": candle.get("date", ""),
                    "open": float(candle.get("open", 0.0)),
                    "high": float(candle.get("high", 0.0)),
                    "low": float(candle.get("low", 0.0)),
                    "close": float(candle.get("close", 0.0)),
                    "volume": int(candle.get("volume", 0)),
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
                timestamp=datetime.utcnow(),
                is_valid=True,
                is_fresh=True,
                confidence=0.97,
                metadata={
                    "source": "fmp",
                    "endpoint": endpoint,
                },
            )
            
        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching OHLCV from FMP for {asset.symbol}: {e}")
            raise ProviderError(f"FMP OHLCV fetch failed: {e}")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data from FMP"""
        logger.info(f"Fetching fundamentals for {asset.symbol} from FMP")
        
        try:
            # Fetch company profile
            profile_endpoint = f"profile/{asset.symbol}"
            profile_data = await self._make_request(profile_endpoint)
            
            if not profile_data or len(profile_data) == 0:
                raise ProviderError(f"No profile data available for {asset.symbol}")
            
            profile = profile_data[0]
            
            # Fetch key metrics
            metrics_endpoint = f"key-metrics/{asset.symbol}"
            metrics_data = await self._make_request(metrics_endpoint)
            
            metrics = metrics_data[0] if metrics_data else {}
            
            # Combine data
            data = {
                "symbol": profile.get("symbol", ""),
                "name": profile.get("companyName", ""),
                "description": profile.get("description", ""),
                "exchange": profile.get("exchange", ""),
                "currency": profile.get("currency", ""),
                "country": profile.get("country", ""),
                "sector": profile.get("sector", ""),
                "industry": profile.get("industry", ""),
                "website": profile.get("website", ""),
                "ceo": profile.get("ceo", ""),
                "employees": int(profile.get("fullTimeEmployees", 0)),
                "market_cap": int(profile.get("mktCap", 0)),
                "price": float(profile.get("price", 0.0)),
                "beta": float(profile.get("beta", 0.0) or 0.0),
                "volume_avg": int(profile.get("volAvg", 0)),
                "last_div": float(profile.get("lastDiv", 0.0) or 0.0),
                "changes": float(profile.get("changes", 0.0) or 0.0),
                # Key metrics
                "pe_ratio": float(metrics.get("peRatio", 0.0) or 0.0),
                "peg_ratio": float(metrics.get("pegRatio", 0.0) or 0.0),
                "pb_ratio": float(metrics.get("pbRatio", 0.0) or 0.0),
                "roe": float(metrics.get("roe", 0.0) or 0.0),
                "roa": float(metrics.get("roa", 0.0) or 0.0),
                "revenue_per_share": float(metrics.get("revenuePerShare", 0.0) or 0.0),
                "net_income_per_share": float(metrics.get("netIncomePerShare", 0.0) or 0.0),
                "operating_cash_flow_per_share": float(metrics.get("operatingCashFlowPerShare", 0.0) or 0.0),
                "free_cash_flow_per_share": float(metrics.get("freeCashFlowPerShare", 0.0) or 0.0),
                "book_value_per_share": float(metrics.get("bookValuePerShare", 0.0) or 0.0),
                "tangible_book_value_per_share": float(metrics.get("tangibleBookValuePerShare", 0.0) or 0.0),
                "shareholders_equity_per_share": float(metrics.get("shareholdersEquityPerShare", 0.0) or 0.0),
                "debt_to_equity": float(metrics.get("debtToEquity", 0.0) or 0.0),
                "debt_to_assets": float(metrics.get("debtToAssets", 0.0) or 0.0),
                "current_ratio": float(metrics.get("currentRatio", 0.0) or 0.0),
                "quick_ratio": float(metrics.get("quickRatio", 0.0) or 0.0),
                "cash_ratio": float(metrics.get("cashRatio", 0.0) or 0.0),
                "gross_profit_margin": float(metrics.get("grossProfitMargin", 0.0) or 0.0),
                "operating_profit_margin": float(metrics.get("operatingProfitMargin", 0.0) or 0.0),
                "net_profit_margin": float(metrics.get("netProfitMargin", 0.0) or 0.0),
            }
            
            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.FUNDAMENTALS,
                data=data,
                timestamp=datetime.utcnow(),
                is_valid=True,
                is_fresh=True,
                confidence=0.96,
                metadata={
                    "source": "fmp",
                    "endpoints": ["profile", "key-metrics"],
                },
            )
            
        except (ProviderError, ProviderTimeoutError, ProviderRateLimitError):
            raise
        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching fundamentals from FMP for {asset.symbol}: {e}")
            raise ProviderError(f"FMP fundamentals fetch failed: {e}")

    async def health_check(self) -> ProviderHealth:
        """Check provider health"""
        try:
            # Simple health check - fetch a known symbol
            test_asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
            await self.fetch_price(test_asset)
            
            return ProviderHealth(
                provider=self.name,
                is_healthy=True,
                latency_ms=100,  # Approximate
                error_rate=self._error_count / max(self._request_count, 1),
                last_check=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"FMP health check failed: {e}")
            return ProviderHealth(
                provider=self.name,
                is_healthy=False,
                latency_ms=0,
                error_rate=1.0,
                last_check=datetime.utcnow(),
                error_message=str(e),
            )

    def _record_request(self) -> None:
        """Record a successful request"""
        self._request_count += 1
        self._last_request_time = datetime.utcnow()

    def _record_error(self) -> None:
        """Record an error"""
        self._error_count += 1
