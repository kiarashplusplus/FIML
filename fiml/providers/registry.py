"""
Provider Registry - Manages all data providers
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fiml.core.config import settings
from fiml.core.exceptions import NoProviderAvailableError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, ProviderHealth
from fiml.providers.base import BaseProvider
from fiml.providers.mock_provider import MockProvider
from fiml.providers.yahoo_finance import YahooFinanceProvider

logger = get_logger(__name__)

# Import new providers conditionally
try:
    from fiml.providers.alpha_vantage import AlphaVantageProvider
    ALPHA_VANTAGE_AVAILABLE = True
except ImportError:
    ALPHA_VANTAGE_AVAILABLE = False
    logger.warning("Alpha Vantage provider not available")

try:
    from fiml.providers.fmp import FMPProvider
    FMP_AVAILABLE = True
except ImportError:
    FMP_AVAILABLE = False
    logger.warning("FMP provider not available")

try:
    from fiml.providers.ccxt_provider import CCXTProvider
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("CCXT provider not available")


class ProviderRegistry:
    """
    Central registry for all data providers

    Manages provider lifecycle, discovery, and selection
    """

    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all providers"""
        if self._initialized:
            logger.warning("Provider registry already initialized")
            return

        logger.info("Initializing provider registry")

        # Register providers based on configuration and availability
        providers_to_register = []
        
        # Always register mock provider for testing
        providers_to_register.append(MockProvider())
        
        # Register Yahoo Finance (free, no API key needed)
        providers_to_register.append(YahooFinanceProvider())
        
        # Register Alpha Vantage if API key is configured
        if ALPHA_VANTAGE_AVAILABLE and settings.alpha_vantage_api_key:
            try:
                providers_to_register.append(AlphaVantageProvider(settings.alpha_vantage_api_key))
                logger.info("Alpha Vantage provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Alpha Vantage provider: {e}")
        
        # Register FMP if API key is configured
        if FMP_AVAILABLE and settings.fmp_api_key:
            try:
                providers_to_register.append(FMPProvider(settings.fmp_api_key))
                logger.info("FMP provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create FMP provider: {e}")
        
        # Register CCXT for crypto (uses Binance by default, no API key needed for public data)
        if CCXT_AVAILABLE:
            try:
                providers_to_register.append(CCXTProvider("binance"))
                logger.info("CCXT Binance provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create CCXT provider: {e}")

        for provider in providers_to_register:
            try:
                await provider.initialize()
                self.providers[provider.name] = provider
                logger.info(f"Registered provider: {provider.name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider.name}: {e}")

        self._initialized = True
        logger.info(f"Provider registry initialized with {len(self.providers)} providers")

    async def shutdown(self) -> None:
        """Shutdown all providers"""
        logger.info("Shutting down provider registry")

        for provider in self.providers.values():
            try:
                await provider.shutdown()
                logger.info(f"Shutdown provider: {provider.name}")
            except Exception as e:
                logger.error(f"Error shutting down provider {provider.name}: {e}")

        self.providers.clear()
        self._initialized = False

    async def get_providers_for_asset(
        self, asset: Asset, data_type: DataType
    ) -> List[BaseProvider]:
        """
        Get all providers that support the given asset and data type

        Args:
            asset: Asset to query
            data_type: Type of data needed

        Returns:
            List of compatible providers, sorted by priority
        """
        compatible_providers = []

        for provider in self.providers.values():
            if not provider.is_enabled:
                continue

            try:
                if await provider.supports_asset(asset):
                    compatible_providers.append(provider)
            except Exception as e:
                logger.error(f"Error checking provider {provider.name} compatibility: {e}")

        # Sort by priority (higher priority first)
        compatible_providers.sort(key=lambda p: p.config.priority, reverse=True)

        if not compatible_providers:
            raise NoProviderAvailableError(
                f"No providers available for asset {asset.symbol} and data type {data_type}"
            )

        return compatible_providers

    async def get_provider_health(self, provider_name: str) -> Optional[ProviderHealth]:
        """Get health status of a specific provider"""
        provider = self.providers.get(provider_name)
        if not provider:
            return None

        try:
            return await provider.get_health()
        except Exception as e:
            logger.error(f"Error getting health for provider {provider_name}: {e}")
            return ProviderHealth(
                provider_name=provider_name,
                is_healthy=False,
                uptime_percent=0.0,
                avg_latency_ms=0.0,
                success_rate=0.0,
                last_check=datetime.now(timezone.utc),
                error_count_24h=1,
            )

    async def get_all_health(self) -> Dict[str, ProviderHealth]:
        """Get health status of all providers"""
        health_status = {}

        for provider_name in self.providers:
            health = await self.get_provider_health(provider_name)
            if health:
                health_status[provider_name] = health

        return health_status


# Global provider registry instance
provider_registry = ProviderRegistry()
