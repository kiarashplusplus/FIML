"""
Provider Registry - Manages all data providers
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fiml.core.config import settings
from fiml.core.exceptions import NoProviderAvailableError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, DataType, ProviderHealth
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

try:
    from fiml.providers.newsapi import NewsAPIProvider
    NEWSAPI_AVAILABLE = True
except ImportError:
    NEWSAPI_AVAILABLE = False
    logger.warning("NewsAPI provider not available")

try:
    from fiml.providers.polygon import PolygonProvider
    POLYGON_AVAILABLE = True
except ImportError:
    POLYGON_AVAILABLE = False
    logger.warning("Polygon provider not available")

try:
    from fiml.providers.finnhub import FinnhubProvider
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False
    logger.warning("Finnhub provider not available")

try:
    from fiml.providers.twelvedata import TwelvedataProvider
    TWELVEDATA_AVAILABLE = True
except ImportError:
    TWELVEDATA_AVAILABLE = False
    logger.warning("Twelvedata provider not available")

try:
    from fiml.providers.tiingo import TiingoProvider
    TIINGO_AVAILABLE = True
except ImportError:
    TIINGO_AVAILABLE = False
    logger.warning("Tiingo provider not available")

try:
    from fiml.providers.intrinio import IntrinioProvider
    INTRINIO_AVAILABLE = True
except ImportError:
    INTRINIO_AVAILABLE = False
    logger.warning("Intrinio provider not available")

try:
    from fiml.providers.marketstack import MarketstackProvider
    MARKETSTACK_AVAILABLE = True
except ImportError:
    MARKETSTACK_AVAILABLE = False
    logger.warning("Marketstack provider not available")

try:
    from fiml.providers.coingecko import CoinGeckoProvider
    COINGECKO_AVAILABLE = True
except ImportError:
    COINGECKO_AVAILABLE = False
    logger.warning("CoinGecko provider not available")

try:
    from fiml.providers.coinmarketcap import CoinMarketCapProvider
    COINMARKETCAP_AVAILABLE = True
except ImportError:
    COINMARKETCAP_AVAILABLE = False
    logger.warning("CoinMarketCap provider not available")

try:
    from fiml.providers.quandl import QuandlProvider
    QUANDL_AVAILABLE = True
except ImportError:
    QUANDL_AVAILABLE = False
    logger.warning("Quandl provider not available")

try:
    from fiml.providers.defillama import DefiLlamaProvider
    DEFILLAMA_AVAILABLE = True
except ImportError:
    DEFILLAMA_AVAILABLE = False
    logger.warning("DefiLlama provider not available")


class ProviderRegistry:
    """
    Central registry for all data providers

    Manages provider lifecycle, discovery, and selection
    """

    def __init__(self) -> None:
        self.providers: Dict[str, BaseProvider] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all providers"""
        if self._initialized:
            logger.warning("Provider registry already initialized")
            return

        logger.info("Initializing provider registry")

        # Register providers based on configuration and availability
        providers_to_register: List[BaseProvider] = []

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

        # Register CCXT exchanges for crypto (public API access - no API key required for market data)
        # These exchanges provide public read access to market data without authentication
        if CCXT_AVAILABLE:
            # List of exchanges with good public API support for price/OHLCV data
            public_exchanges = [
                "kraken",      # Well-established, reliable public API
                "kucoin",      # Good public data access
                "okx",         # Major exchange with public data
                "bybit",       # Derivatives focused, good public API
                "gateio",      # Wide token coverage
                "bitget",      # Growing exchange with public data
            ]
            for exchange_id in public_exchanges:
                try:
                    providers_to_register.append(CCXTProvider(exchange_id))
                    logger.info(f"CCXT {exchange_id} provider will be registered (public API)")
                except Exception as e:
                    logger.warning(f"Could not create CCXT {exchange_id} provider: {e}")

        # Register NewsAPI if API key is configured
        newsapi_key = settings.newsapi_api_key or settings.newsapi_key
        if NEWSAPI_AVAILABLE and newsapi_key and settings.newsapi_enabled:
            try:
                providers_to_register.append(NewsAPIProvider(newsapi_key))
                logger.info("NewsAPI provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create NewsAPI provider: {e}")

        # Register Polygon if API key is configured
        if POLYGON_AVAILABLE and settings.polygon_api_key:
            try:
                providers_to_register.append(PolygonProvider(settings.polygon_api_key))
                logger.info("Polygon provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Polygon provider: {e}")

        # Register Finnhub if API key is configured
        if FINNHUB_AVAILABLE and settings.finnhub_api_key:
            try:
                providers_to_register.append(FinnhubProvider(settings.finnhub_api_key))
                logger.info("Finnhub provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Finnhub provider: {e}")

        # Register Twelvedata if API key is configured
        if TWELVEDATA_AVAILABLE and settings.twelvedata_api_key:
            try:
                providers_to_register.append(TwelvedataProvider(settings.twelvedata_api_key))
                logger.info("Twelvedata provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Twelvedata provider: {e}")

        # Register Tiingo if API key is configured
        if TIINGO_AVAILABLE and settings.tiingo_api_key:
            try:
                providers_to_register.append(TiingoProvider(settings.tiingo_api_key))
                logger.info("Tiingo provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Tiingo provider: {e}")

        # Register Intrinio if API key is configured
        if INTRINIO_AVAILABLE and settings.intrinio_api_key:
            try:
                providers_to_register.append(IntrinioProvider(settings.intrinio_api_key))
                logger.info("Intrinio provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Intrinio provider: {e}")

        # Register Marketstack if API key is configured
        if MARKETSTACK_AVAILABLE and settings.marketstack_api_key:
            try:
                providers_to_register.append(MarketstackProvider(settings.marketstack_api_key))
                logger.info("Marketstack provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Marketstack provider: {e}")

        # Register CoinGecko (no API key needed for basic tier)
        if COINGECKO_AVAILABLE:
            try:
                providers_to_register.append(CoinGeckoProvider())
                logger.info("CoinGecko provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create CoinGecko provider: {e}")

        # Register DefiLlama (no API key needed - free API)
        if DEFILLAMA_AVAILABLE:
            try:
                providers_to_register.append(DefiLlamaProvider())
                logger.info("DefiLlama provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create DefiLlama provider: {e}")

        # Register CoinMarketCap if API key is configured
        if COINMARKETCAP_AVAILABLE and settings.coinmarketcap_api_key:
            try:
                providers_to_register.append(CoinMarketCapProvider(settings.coinmarketcap_api_key))
                logger.info("CoinMarketCap provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create CoinMarketCap provider: {e}")

        # Register Quandl if API key is configured
        if QUANDL_AVAILABLE and settings.quandl_api_key:
            try:
                providers_to_register.append(QuandlProvider(settings.quandl_api_key))
                logger.info("Quandl provider will be registered")
            except Exception as e:
                logger.warning(f"Could not create Quandl provider: {e}")

        for provider in providers_to_register:
            try:
                await provider.initialize()
                # Only register providers that successfully initialized
                if provider._is_initialized:
                    self.providers[provider.name] = provider
                    logger.info(f"Registered provider: {provider.name}")
                else:
                    logger.warning(f"Provider {provider.name} not initialized - skipping registration")
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

    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """
        Get a specific provider by name

        Args:
            provider_name: Name of the provider

        Returns:
            Provider instance or None if not found
        """
        return self.providers.get(provider_name)

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
