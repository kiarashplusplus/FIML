"""
Base Provider Interface
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from fiml.core.models import Asset, DataType, ProviderHealth


class ProviderConfig(BaseModel):
    """Provider configuration"""

    name: str
    enabled: bool = True
    priority: int = 1
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 5
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class ProviderResponse(BaseModel):
    """Standardized provider response"""

    provider: str
    asset: Asset
    data_type: DataType
    data: Dict[str, Any]
    timestamp: datetime
    is_valid: bool = True
    is_fresh: bool = True
    confidence: float = 1.0
    metadata: Dict[str, Any] = {}


class BaseProvider(ABC):
    """
    Base class for all data providers

    All providers must implement this interface to be compatible
    with the data arbitration engine.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self._request_count = 0
        self._error_count = 0
        self._last_request_time: Optional[datetime] = None
        self._is_initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (API clients, connections, etc.)"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources"""
        pass

    @abstractmethod
    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch current price data"""
        pass

    @abstractmethod
    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch OHLCV (candlestick) data"""
        pass

    @abstractmethod
    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch fundamental data (for equities)"""
        pass

    @abstractmethod
    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles"""
        pass

    @abstractmethod
    async def supports_asset(self, asset: Asset) -> bool:
        """Check if provider supports this asset type"""
        pass

    @abstractmethod
    async def get_health(self) -> ProviderHealth:
        """Get provider health metrics"""
        pass

    async def get_latency_p95(self, region: str = "US") -> float:
        """Get 95th percentile latency for region (in ms)"""
        # TODO: Implement actual latency tracking
        return 100.0

    async def get_last_update(self, asset: Asset, data_type: DataType) -> datetime:
        """Get timestamp of last successful update"""
        # TODO: Implement actual tracking
        return datetime.now(timezone.utc)

    async def get_completeness(self, data_type: DataType) -> float:
        """Get data completeness score (0.0 - 1.0)"""
        # TODO: Implement actual completeness tracking
        return 1.0

    async def get_success_rate(self) -> float:
        """Get success rate over last N requests"""
        if self._request_count == 0:
            return 1.0
        return 1.0 - (self._error_count / self._request_count)

    async def get_uptime_24h(self) -> float:
        """Get uptime percentage over last 24 hours"""
        # TODO: Implement actual uptime tracking
        return 0.99

    def _record_request(self) -> None:
        """Record a request"""
        self._request_count += 1
        self._last_request_time = datetime.now(timezone.utc)

    def _record_error(self) -> None:
        """Record an error"""
        self._error_count += 1

    @property
    def is_enabled(self) -> bool:
        """Check if provider is enabled"""
        return self.config.enabled and self._is_initialized
