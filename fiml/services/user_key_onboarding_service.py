"""
User Key Onboarding Service - Platform-agnostic BYOK implementation

This service provides a unified interface for managing user API keys across
all FIML platforms (Telegram, Web, ChatGPT Plugin).

Key features:
- Platform-agnostic key operations
- Pluggable storage backends (file, database, cloud)
- Encryption/decryption handling
- Provider validation and testing
- Quota tracking
"""

import re
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import aiohttp
import structlog
from cryptography.fernet import Fernet

from fiml.services.storage import KeyStorageInterface

logger = structlog.get_logger(__name__)


class UserKeyOnboardingService:
    """
    Platform-agnostic service for managing user API keys (BYOK model)

    This service coordinates between:
    - Encryption (Fernet)
    - Storage backend (file, db, cloud)
    - Provider validation
    - Usage tracking

    Example usage:
        # Telegram bot
        storage = FileKeyStorage(path="./data/keys")
        service = UserKeyOnboardingService(storage)

        # Web app
        storage = DatabaseKeyStorage(pool=db_pool)
        service = UserKeyOnboardingService(storage)
    """

    # Provider key format patterns (from original UserProviderKeyManager)
    KEY_PATTERNS = {
        "alpha_vantage": r"^[A-Z0-9]{16}$",
        "polygon": r"^[A-Za-z0-9_-]{32}$",
        "finnhub": r"^[a-z0-9]{20}$",
        "fmp": r"^[a-z0-9]{32}$",
    }

    # Provider information
    PROVIDER_INFO = {
        "alpha_vantage": {
            "name": "Alpha Vantage",
            "asset_types": ["stocks", "forex", "crypto"],
            "free_tier": True,
            "free_limit": "5 requests/minute, 500/day",
            "signup_url": "https://www.alphavantage.co/support/#api-key",
        },
        "polygon": {
            "name": "Polygon.io",
            "asset_types": ["stocks", "options", "forex", "crypto"],
            "free_tier": False,
            "paid_tiers": "Starter $199/mo, Developer $399/mo",
            "signup_url": "https://polygon.io/pricing",
        },
        "finnhub": {
            "name": "Finnhub",
            "asset_types": ["stocks", "forex", "crypto"],
            "free_tier": True,
            "free_limit": "60 requests/minute",
            "signup_url": "https://finnhub.io/pricing",
        },
        "fmp": {
            "name": "Financial Modeling Prep",
            "asset_types": ["stocks", "crypto", "forex"],
            "free_tier": True,
            "free_limit": "250 requests/day",
            "signup_url": "https://site.financialmodelingprep.com/developer/docs",
        },
    }

    def __init__(self, storage: KeyStorageInterface, encryption_key: Optional[bytes] = None):
        """
        Initialize user key onboarding service

        Args:
            storage: Storage backend implementation
            encryption_key: Fernet encryption key (generated if not provided)
        """
        self.storage = storage
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)

        # In-memory quota tracking (temporary - should be Redis)
        self._quota_usage: Dict[str, int] = {}

        logger.info("UserKeyOnboardingService initialized", storage=type(storage).__name__)

    # ======================================================================
    # Core Key Management Operations
    # ======================================================================

    async def add_key(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        validate: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add/update API key for a user

        Args:
            user_id: User identifier (platform-specific)
            provider: Provider identifier
            api_key: Raw (unencrypted) API key
            validate: Whether to test key with provider API
            metadata: Optional metadata to store  (overrides validation metadata)

        Returns:
            Dict with success status and details
        """
        try:
            # Format validation
            if not self.validate_key_format(provider, api_key):
                return {"success": False, "error": f"Invalid key format for {provider}"}

            # API validation (if requested and no metadata provided)
            if validate and not metadata:
                test_result = await self.test_key(provider, api_key)
                if not test_result["valid"]:
                    return {
                        "success": False,
                        "error": f"Key validation failed: {test_result['message']}",
                    }
                metadata = {
                    "tier": test_result.get("tier"),
                    "validated_at": datetime.now(UTC).isoformat(),
                }
            elif not metadata:
                metadata = {}

            # Encrypt key
            encrypted_key = self.cipher.encrypt(api_key.encode()).decode()

            # Store via backend
            success = await self.storage.store(user_id, provider, encrypted_key, metadata)

            if success:
                logger.info("Key added", user_id=user_id, provider=provider)
                return {"success": True, "provider": provider, "metadata": metadata}
            else:
                return {"success": False, "error": "Storage operation failed"}

        except Exception as e:
            logger.error("Failed to add key", user_id=user_id, provider=provider, error=str(e))
            return {"success": False, "error": str(e)}

    async def get_key(self, user_id: str, provider: str) -> Optional[str]:
        """
        Retrieve and decrypt API key

        Args:
            user_id: User identifier
            provider: Provider identifier

        Returns:
            Decrypted API key or None if not found
        """
        try:
            # Retrieve from storage
            key_data = await self.storage.retrieve(user_id, provider)

            if not key_data or "encrypted_key" not in key_data:
                return None

            # Decrypt
            encrypted_key = key_data["encrypted_key"].encode()
            decrypted_key: str = self.cipher.decrypt(encrypted_key).decode()

            return decrypted_key

        except Exception as e:
            logger.error("Failed to get key", user_id=user_id, provider=provider, error=str(e))
            return None

    async def remove_key(self, user_id: str, provider: str) -> bool:
        """
        Remove API key for provider

        Args:
            user_id: User identifier
            provider: Provider identifier

        Returns:
            True if removed successfully
        """
        try:
            success = await self.storage.delete(user_id, provider)

            if success:
                logger.info("Key removed", user_id=user_id, provider=provider)

            return success

        except Exception as e:
            logger.error("Failed to remove key", user_id=user_id, provider=provider, error=str(e))
            return False

    async def list_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all providers user has keys for

        Args:
            user_id: User identifier

        Returns:
            List of provider info dicts with metadata
        """
        try:
            providers = await self.storage.list_all(user_id)

            result = []
            for provider in providers:
                key_data = await self.storage.retrieve(user_id, provider)
                provider_info = self.PROVIDER_INFO.get(provider, {})

                result.append(
                    {
                        "provider": provider,
                        "name": provider_info.get("name", provider),
                        "added_at": key_data.get("added_at") if key_data else None,
                        "metadata": key_data.get("metadata", {}) if key_data else {},
                    }
                )

            return result

        except Exception as e:
            logger.error("Failed to list keys", user_id=user_id, error=str(e))
            return []

    async def get_all_keys(self, user_id: str) -> Dict[str, str]:
        """
        Get all decrypted keys for user

        Args:
            user_id: User identifier

        Returns:
            Dict mapping provider -> decrypted_key
        """
        try:
            all_key_data = await self.storage.get_all_keys(user_id)

            decrypted_keys = {}
            for provider, key_data in all_key_data.items():
                encrypted_key = key_data["encrypted_key"].encode()
                decrypted_key = self.cipher.decrypt(encrypted_key).decode()
                decrypted_keys[provider] = decrypted_key

            return decrypted_keys

        except Exception as e:
            logger.error("Failed to get all keys", user_id=user_id, error=str(e))
            return {}

    # ======================================================================
    # Validation Methods
    # ======================================================================

    def validate_key_format(self, provider: str, api_key: str) -> bool:
        """
        Validate API key format using regex pattern

        Args:
            provider: Provider identifier
            api_key: API key to validate

        Returns:
            True if format is valid
        """
        pattern = self.KEY_PATTERNS.get(provider)
        if not pattern:
            logger.warning("No pattern for provider", provider=provider)
            return True  # Allow unknown providers

        is_valid = bool(re.match(pattern, api_key))
        logger.debug(
            "Key format validation", provider=provider, valid=is_valid, key_length=len(api_key)
        )
        return is_valid

    async def test_key(self, provider: str, api_key: str) -> Dict[str, Any]:
        """
        Test API key by making live API call

        Args:
            provider: Provider identifier
            api_key: API key to test

        Returns:
            Dict with test results: {valid: bool, tier: str, message: str}
        """
        logger.info("Testing provider key", provider=provider)

        try:
            if provider == "alpha_vantage":
                return await self._test_alpha_vantage(api_key)
            elif provider == "polygon":
                return await self._test_polygon(api_key)
            elif provider == "finnhub":
                return await self._test_finnhub(api_key)
            elif provider == "fmp":
                return await self._test_fmp(api_key)
            else:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": f"Provider {provider} not yet supported for testing",
                }
        except Exception as e:
            logger.error("Key test failed", provider=provider, error=str(e))
            return {"valid": False, "tier": "unknown", "message": f"Test failed: {str(e)}"}

    # ======================================================================
    # Provider-Specific API Tests (from UserProviderKeyManager)
    # ======================================================================

    async def _test_alpha_vantage(self, api_key: str) -> Dict[str, Any]:
        """Test Alpha Vantage API key"""
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": "IBM",
            "interval": "5min",
            "apikey": api_key,
        }

        timeout = aiohttp.ClientTimeout(total=10)
        async with (
            aiohttp.ClientSession() as session,
            session.get(url, params=params, timeout=timeout) as resp,
        ):
            data = await resp.json()

            if "Error Message" in data:
                return {"valid": False, "tier": "unknown", "message": "Invalid API key"}
            elif "Note" in data or "Time Series (5min)" in data:
                return {
                    "valid": True,
                    "tier": "free",
                    "message": "Free tier (5 requests/minute, 500/day)",
                }
            else:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Unexpected response from API",
                }

    async def _test_polygon(self, api_key: str) -> Dict[str, Any]:
        """Test Polygon.io API key"""
        url = "https://api.polygon.io/v2/aggs/ticker/AAPL/prev"
        headers = {"Authorization": f"Bearer {api_key}"}

        timeout = aiohttp.ClientTimeout(total=10)
        async with (
            aiohttp.ClientSession() as session,
            session.get(url, headers=headers, timeout=timeout) as resp,
        ):
            if resp.status == 200:
                return {"valid": True, "tier": "paid", "message": "Polygon.io key validated"}
            elif resp.status == 401:
                return {"valid": False, "tier": "unknown", "message": "Invalid API key"}
            else:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": f"API returned status {resp.status}",
                }

    async def _test_finnhub(self, api_key: str) -> Dict[str, Any]:
        """Test Finnhub API key"""
        url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}"

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session, session.get(url, timeout=timeout) as resp:
            data = await resp.json()

            if "error" in data:
                return {"valid": False, "tier": "unknown", "message": "Invalid API key"}
            elif "c" in data:  # Current price
                return {"valid": True, "tier": "free", "message": "Free tier (60 requests/minute)"}
            else:
                return {"valid": False, "tier": "unknown", "message": "Unexpected response"}

    async def _test_fmp(self, api_key: str) -> Dict[str, Any]:
        """Test Financial Modeling Prep API key"""
        url = f"https://financialmodelingprep.com/api/v3/quote/AAPL?apikey={api_key}"

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session, session.get(url, timeout=timeout) as resp:
            data = await resp.json()

            if isinstance(data, dict) and "Error Message" in data:
                return {"valid": False, "tier": "unknown", "message": "Invalid API key"}
            elif isinstance(data, list) and len(data) > 0:
                return {"valid": True, "tier": "free", "message": "Free tier (250 requests/day)"}
            else:
                return {"valid": False, "tier": "unknown", "message": "Unexpected response"}

    # ======================================================================
    # Provider Information
    # ======================================================================

    def get_provider_info(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider"""
        return self.PROVIDER_INFO.get(provider)

    def list_supported_providers(self) -> List[Dict[str, Any]]:
        """List all supported providers with their information"""
        return [{"id": key, **value} for key, value in self.PROVIDER_INFO.items()]

    # ======================================================================
    # Quota Tracking (simplified - should use Redis in production)
    # ======================================================================

    async def track_usage(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Track API usage for quota management"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"{user_id}:{provider}:{today}"

        if key not in self._quota_usage:
            self._quota_usage[key] = 0

        self._quota_usage[key] += 1
        usage = self._quota_usage[key]

        # Simplified limits (should come from provider metadata)
        limits = {
            "alpha_vantage": 400,  # 80% of 500
            "fmp": 200,  # 80% of 250
            "finnhub": 2000,  # Reasonable daily limit
        }

        limit = limits.get(provider, 1000)

        if usage >= limit:
            logger.warning(
                "Quota warning", user_id=user_id, provider=provider, usage=usage, limit=limit
            )
            return {"warning": True, "usage": usage, "limit": limit}

        return {"warning": False, "usage": usage, "limit": limit}

    async def get_usage(self, user_id: str, provider: str) -> int:
        """Get current usage for user/provider"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"{user_id}:{provider}:{today}"
        return self._quota_usage.get(key, 0)
