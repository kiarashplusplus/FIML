"""
Mock Provider for Testing
"""

from datetime import datetime
from typing import Dict

from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse


class MockProvider(BaseProvider):
    """
    Mock provider for testing and development

    Returns synthetic data without external API calls
    """

    def __init__(self):
        config = ProviderConfig(
            name="mock_provider",
            enabled=True,
            priority=1,
            rate_limit_per_minute=1000,
            timeout_seconds=1,
        )
        super().__init__(config)

    async def initialize(self) -> None:
        """Initialize mock provider"""
        self._is_initialized = True

    async def shutdown(self) -> None:
        """Shutdown mock provider"""
        self._is_initialized = False

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """Fetch mock price data"""
        self._record_request()

        # Generate synthetic price data
        mock_price = 100.0 if asset.asset_type == AssetType.EQUITY else 40000.0

        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.PRICE,
            data={
                "price": mock_price,
                "change": -1.5,
                "change_percent": -1.48,
                "volume": 1000000,
            },
            timestamp=datetime.utcnow(),
            is_valid=True,
            is_fresh=True,
            confidence=1.0,
            metadata={"source": "mock"},
        )

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """Fetch mock OHLCV data"""
        self._record_request()

        # Generate synthetic OHLCV data
        mock_candles = [
            {
                "timestamp": datetime.utcnow(),
                "open": 100.0,
                "high": 105.0,
                "low": 98.0,
                "close": 102.0,
                "volume": 1000000,
            }
            for _ in range(limit)
        ]

        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.OHLCV,
            data={"candles": mock_candles, "timeframe": timeframe},
            timestamp=datetime.utcnow(),
            is_valid=True,
            is_fresh=True,
            confidence=1.0,
        )

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """Fetch mock fundamental data"""
        self._record_request()

        mock_fundamentals = {
            "market_cap": 100000000000,
            "pe_ratio": 25.5,
            "eps": 4.5,
            "beta": 1.2,
            "dividend_yield": 0.02,
            "sector": "Technology",
            "industry": "Software",
        }

        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.FUNDAMENTALS,
            data=mock_fundamentals,
            timestamp=datetime.utcnow(),
            is_valid=True,
            is_fresh=True,
            confidence=1.0,
        )

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch mock news data"""
        self._record_request()

        mock_news = [
            {
                "title": f"Mock news article {i}",
                "url": f"https://example.com/news/{i}",
                "published_at": datetime.utcnow(),
                "sentiment": 0.5,
            }
            for i in range(limit)
        ]

        return ProviderResponse(
            provider=self.name,
            asset=asset,
            data_type=DataType.NEWS,
            data={"articles": mock_news},
            timestamp=datetime.utcnow(),
            is_valid=True,
            is_fresh=True,
            confidence=0.8,
        )

    async def supports_asset(self, asset: Asset) -> bool:
        """Mock provider supports all asset types"""
        return True

    async def get_health(self) -> ProviderHealth:
        """Get mock provider health"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=True,
            uptime_percent=1.0,
            avg_latency_ms=10.0,
            success_rate=await self.get_success_rate(),
            last_check=datetime.utcnow(),
            error_count_24h=0,
        )
