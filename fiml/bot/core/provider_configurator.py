"""
Component 2: FIML Provider Configurator
Configures FIML arbitration engine with user-specific API keys
"""

from typing import TYPE_CHECKING, Dict, List, Optional

import structlog

if TYPE_CHECKING:
    from fiml.bot.core.key_manager import UserProviderKeyManager

logger = structlog.get_logger(__name__)


class FIMLProviderConfigurator:
    """
    Configures FIML data arbitration engine with user-specific providers

    Features:
    - Per-user provider configuration
    - Priority-based provider selection (user keys > platform keys)
    - Automatic fallback to free providers
    - Usage tracking and quota management
    """

    # Known providers that support API keys
    KNOWN_PROVIDERS = ["alpha_vantage", "polygon", "finnhub", "fmp"]

    # Free providers that don't require API keys
    FREE_PROVIDERS = ["yahoo_finance"]

    # Provider fallback mappings
    FALLBACK_MAP = {
        "alpha_vantage": ["yahoo_finance", "finnhub"],
        "polygon": ["alpha_vantage", "yahoo_finance"],
        "finnhub": ["alpha_vantage", "yahoo_finance"],
        "fmp": ["alpha_vantage", "yahoo_finance"],
    }

    def __init__(self, key_manager: Optional['UserProviderKeyManager'] = None):
        """
        Initialize configurator

        Args:
            key_manager: User provider key manager instance (optional, created if not provided)
        """
        if key_manager is None:
            from fiml.bot.core.key_manager import UserProviderKeyManager
            key_manager = UserProviderKeyManager()
        self.key_manager = key_manager
        logger.info("FIMLProviderConfigurator initialized")

    def get_user_provider_config(self, user_id: str, user_keys: Optional[Dict] = None) -> Dict:
        """
        Get user's provider configuration for FIML (synchronous)

        Note: This method is synchronous and does not fetch keys from key_manager.
        If user_keys is None, defaults to empty dict for free-tier-only configuration.

        Args:
            user_id: User identifier
            user_keys: User keys dict (optional - if not provided, defaults to empty dict
                resulting in free-tier-only configuration)

        Returns:
            Provider configuration dict
        """
        # Default to empty dict if not provided (free tier only)
        if user_keys is None:
            user_keys = {}

        config = {
            "user_id": user_id,
            "providers": [],
            "fallback_enabled": True,
            "fallback_provider": "yahoo_finance",
            "free_tier": len(user_keys) == 0
        }

        # Add user's providers (Priority 1-2)
        for provider, key_data in user_keys.items():
            # Handle both dict format and string format
            if isinstance(key_data, dict):
                api_key = key_data.get("key", "")
                tier = key_data.get("tier", "free")
            else:
                api_key = key_data
                tier = "free"

            config["providers"].append({
                "name": provider,
                "api_key": api_key,
                "priority": 1 if tier == "paid" else 2,
                "user_provided": True,
            })

        # Always add free providers as fallback (Priority 3)
        config["providers"].append({
            "name": "yahoo_finance",
            "api_key": None,  # No key required
            "priority": 3,
            "user_provided": False,
        })

        # Sort by priority
        config["providers"].sort(key=lambda p: p["priority"])

        logger.info(
            "User provider config built",
            user_id=user_id,
            num_providers=len(config["providers"]),
            has_user_keys=len(user_keys) > 0
        )

        return config

    async def get_fiml_client_for_user(self, user_id: str):
        """
        Get FIML client configured for user's providers

        Args:
            user_id: User identifier

        Returns:
            Configured FIML client instance
        """
        from fiml.arbitration.engine import DataArbitrationEngine

        # Get user's stored API keys
        user_keys = await self.key_manager.get_user_keys(user_id)

        # Get user's provider configuration
        config = self.get_user_provider_config(user_id, user_keys=user_keys)

        # Initialize providers
        providers = []
        for provider_config in config["providers"]:
            try:
                provider_name = provider_config["name"]
                api_key = provider_config.get("api_key")

                # Get provider instance
                if provider_name == "yahoo_finance":
                    from fiml.providers.yahoo_finance import YahooFinanceProvider
                    provider = YahooFinanceProvider()
                elif provider_name == "alpha_vantage" and api_key:
                    from fiml.providers.alpha_vantage import AlphaVantageProvider
                    provider = AlphaVantageProvider(api_key=api_key)
                elif provider_name == "polygon" and api_key:
                    from fiml.providers.polygon_provider import PolygonProvider
                    provider = PolygonProvider(api_key=api_key)
                elif provider_name == "finnhub" and api_key:
                    from fiml.providers.finnhub import FinnhubProvider
                    provider = FinnhubProvider(api_key=api_key)
                elif provider_name == "fmp" and api_key:
                    from fiml.providers.fmp import FMPProvider
                    provider = FMPProvider(api_key=api_key)
                else:
                    logger.warning(
                        "Skipping unsupported provider",
                        provider=provider_name
                    )
                    continue

                providers.append(provider)

            except Exception as e:
                logger.error(
                    "Failed to initialize provider",
                    provider=provider_config["name"],
                    error=str(e)
                )

        # Initialize arbitration engine with user's providers
        engine = DataArbitrationEngine(providers=providers)

        logger.info(
            "FIML client configured for user",
            user_id=user_id,
            num_providers=len(providers)
        )

        return engine

    async def track_provider_usage(
        self,
        user_id: str,
        provider: str,
        query_type: str
    ):
        """
        Track API usage for quota management

        Args:
            user_id: User identifier
            provider: Provider name
            query_type: Type of query (e.g., "stock_quote")
        """
        # Track in key manager
        usage_info = await self.key_manager.track_usage(user_id, provider)

        # Return warning if quota threshold reached
        if usage_info.get("warning"):
            logger.warning(
                "User quota warning",
                user_id=user_id,
                provider=provider,
                usage=usage_info["usage"],
                limit=usage_info["limit"]
            )
            return {
                "warning": True,
                "message": f"You've used {usage_info['usage']}/{usage_info['limit']} "
                          f"requests for {provider} today",
                "usage": usage_info["usage"],
                "limit": usage_info["limit"]
            }

        return {"warning": False}

    async def handle_provider_error(
        self,
        user_id: str,
        provider: str,
        error: Exception
    ) -> Dict:
        """
        Handle provider errors and determine fallback strategy

        Args:
            user_id: User identifier
            provider: Provider that failed
            error: Exception that occurred

        Returns:
            Error handling response with fallback suggestions
        """
        error_type = type(error).__name__
        error_msg = str(error)

        logger.error(
            "Provider error",
            user_id=user_id,
            provider=provider,
            error_type=error_type,
            error_msg=error_msg
        )

        # Determine error category
        if "401" in error_msg or "Invalid API key" in error_msg:
            return {
                "error_type": "invalid_key",
                "message": f"Your {provider} API key appears to be invalid. "
                          "Please update it with /addkey",
                "fallback": "yahoo_finance",
                "action": "update_key"
            }

        elif "429" in error_msg or "quota" in error_msg.lower():
            return {
                "error_type": "quota_exceeded",
                "message": f"You've exceeded your {provider} quota. "
                          "Falling back to free providers.",
                "fallback": "yahoo_finance",
                "action": "wait_or_upgrade"
            }

        else:
            return {
                "error_type": "api_error",
                "message": f"{provider} is experiencing issues. "
                          "Using alternative providers.",
                "fallback": "yahoo_finance",
                "action": "retry_later"
            }

    def get_fallback_suggestions(self, failed_provider: str) -> List[str]:
        """
        Get fallback provider suggestions when a provider fails

        Args:
            failed_provider: Name of the provider that failed

        Returns:
            List of suggested fallback provider names
        """
        # Use class constant for fallback mappings
        suggestions = self.FALLBACK_MAP.get(failed_provider, self.FREE_PROVIDERS)

        logger.info(
            "Generated fallback suggestions",
            failed_provider=failed_provider,
            suggestions=suggestions
        )

        return suggestions

    def check_provider_health(self, provider: str) -> bool:
        """
        Check if a provider is healthy and available

        Args:
            provider: Provider name to check

        Returns:
            True if provider is healthy, False otherwise
        """
        # Free providers are always available (no API key required)
        if provider in self.FREE_PROVIDERS:
            return True

        # For other providers, check if they're in our known list
        is_healthy = provider in self.KNOWN_PROVIDERS

        logger.info(
            "Provider health check",
            provider=provider,
            is_healthy=is_healthy
        )

        return is_healthy

    async def get_provider_status(self, user_id: str) -> List[Dict]:
        """
        Get status of all user's providers

        Args:
            user_id: User identifier

        Returns:
            List of provider status dicts
        """
        providers = await self.key_manager.list_user_providers(user_id)

        status_list = []
        for provider_info in providers:
            provider = provider_info["provider"]

            # Get usage
            usage = await self.key_manager.get_usage(user_id, provider)

            # Get provider info
            info = self.key_manager.get_provider_info(provider)

            status_list.append({
                "provider": provider,
                "name": info.get("name", provider) if info else provider,
                "added_at": provider_info.get("added_at"),
                "usage_today": usage,
                "tier": provider_info.get("metadata", {}).get("tier", "unknown"),
                "status": "active"  # Could add health checks here
            })

        return status_list
