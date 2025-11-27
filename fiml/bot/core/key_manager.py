"""
Component 1: User Provider Key Manager
Handles collection, validation, and secure storage of user API keys (BYOK model)
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from cryptography.fernet import Fernet

logger = structlog.get_logger(__name__)


class UserProviderKeyManager:
    """
    Manages user-provided API keys for data providers (BYOK model)

    Features:
    - Secure key storage with encryption
    - Key validation (format + API test)
    - Quota tracking
    - Multi-provider support
    """

    # Provider key format patterns
    KEY_PATTERNS = {
        "alpha_vantage": r"^[A-Z0-9]{16}$",
        "polygon": r"^[A-Za-z0-9_-]{32}$",
        "finnhub": r"^[a-z0-9]{20}$",
        "fmp": r"^[a-z0-9]{32}$",
    }

    # Provider information for user guidance
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

    def __init__(self, encryption_key: Optional[bytes] = None, storage_path: str = "./data/keys"):
        """
        Initialize key manager (now wraps UserKeyOnboardingService)

        Args:
            encryption_key: Fernet encryption key (generated if not provided)
            storage_path: Path to store encrypted keys
        """
        # Initialize new service architecture
        from fiml.services import UserKeyOnboardingService
        from fiml.services.storage.file_storage import FileKeyStorage

        self.encryption_key = encryption_key or Fernet.generate_key()
        self.storage_path = Path(storage_path)

        # Create file storage backend
        file_storage = FileKeyStorage(storage_path=str(self.storage_path))

        # Initialize service with file storage
        self._service = UserKeyOnboardingService(
            storage=file_storage, encryption_key=self.encryption_key
        )

        # Provide direct access to cipher for backward compatibility
        self.cipher = self._service.cipher

        # In-memory cache for decrypted keys (session-scoped) - now delegated to service
        self._key_cache: Dict[str, Dict[str, str]] = {}

        # Quota tracking - now delegated to service
        self._quota_usage: Dict[str, int] = self._service._quota_usage

        logger.info(
            "UserProviderKeyManager initialized (using new service layer)",
            storage_path=storage_path,
        )

    def get_provider_info(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider for user guidance"""
        return self._service.get_provider_info(provider)

    def list_supported_providers(self) -> List[Dict[str, Any]]:
        """List all supported providers with their information"""
        return self._service.list_supported_providers()

    def validate_key_format(self, provider: str, api_key: str) -> bool:
        """
        Validate API key format using regex pattern

        Args:
            provider: Provider identifier
            api_key: API key to validate

        Returns:
            True if format is valid
        """
        return self._service.validate_key_format(provider, api_key)

    async def test_provider_key(self, provider: str, api_key: str) -> Dict[str, Any]:
        """
        Test API key by making actual API call

        Args:
            provider: Provider identifier
            api_key: API key to test

        Returns:
            Dict with test results: {valid: bool, tier: str, message: str}
        """
        return await self._service.test_key(provider, api_key)

    # Provider tests removed - now handled by service layer
    # (Methods _test_alpha_vantage, _test_polygon, _test_finnhub, _test_fmp deleted)

    async def store_user_key(
        self, user_id: str, provider: str, api_key: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Encrypt and store user API key (delegates to service)

        Args:
            user_id: User identifier
            provider: Provider identifier
            api_key: API key to store
            metadata: Optional metadata (tier, limits, etc.)

        Returns:
            True if stored successfully
        """
        result = await self._service.add_key(
            user_id, provider, api_key, validate=False, metadata=metadata
        )

        # Update cache for backward compatibility
        if result["success"]:
            if user_id not in self._key_cache:
                self._key_cache[user_id] = {}
            self._key_cache[user_id][provider] = api_key

        success: bool = result["success"]
        return success

    async def get_user_keys(self, user_id: str) -> Dict[str, str]:
        """
        Retrieve and decrypt user's API keys

        Args:
            user_id: User identifier

        Returns:
            Dict of provider -> api_key
        """
        # Check cache first
        if user_id in self._key_cache:
            return self._key_cache[user_id].copy()

        # Get from service
        keys = await self._service.get_all_keys(user_id)

        # Update cache
        self._key_cache[user_id] = keys.copy()

        return keys

    async def remove_user_key(self, user_id: str, provider: str) -> bool:
        """
        Remove a user's API key for a provider

        Args:
            user_id: User identifier
            provider: Provider to remove

        Returns:
            True if removed successfully
        """
        success = await self._service.remove_key(user_id, provider)

        # Update cache
        if success and user_id in self._key_cache and provider in self._key_cache[user_id]:
            del self._key_cache[user_id][provider]

        return success

    async def list_user_providers(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all providers user has keys for

        Args:
            user_id: User identifier

        Returns:
            List of provider info dicts
        """
        user_file = self.storage_path / f"{user_id}.json"

        try:
            import os

            if not os.path.exists(user_file):
                return []

            with open(user_file, "r") as f:
                user_keys_data = json.load(f)

            providers = []
            for provider, key_data in user_keys_data.items():
                provider_info = self.PROVIDER_INFO.get(provider, {})
                providers.append(
                    {
                        "provider": provider,
                        "name": provider_info.get("name", provider),
                        "added_at": key_data.get("added_at"),
                        "metadata": key_data.get("metadata", {}),
                    }
                )

            return providers

        except Exception as e:
            logger.error("Failed to list providers", user_id=user_id, error=str(e))
            return []

    async def track_usage(self, user_id: str, provider: str) -> Dict[str, Any]:
        """
        Track API usage for quota management

        Args:
            user_id: User identifier
            provider: Provider used
        """
        # In-memory tracking (should be Redis in production)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"{user_id}:{provider}:{today}"

        if key not in self._quota_usage:
            self._quota_usage[key] = 0

        self._quota_usage[key] += 1

        # Get usage
        usage = self._quota_usage[key]

        # Check if warning needed (simplified - should check actual provider limits)
        # For now, warn at 80% of free tier limits
        limits = {
            "alpha_vantage": 400,  # 80% of 500
            "fmp": 200,  # 80% of 250
            "finnhub": 2000,  # 80% of some reasonable daily limit
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

    async def _audit_log(self, user_id: str, action: str) -> None:
        """
        Log key management actions for audit trail

        Args:
            user_id: User identifier
            action: Action description
        """
        logger.info(
            "Key management audit",
            user_id=user_id,
            action=action,
            timestamp=datetime.now(UTC).isoformat(),
        )

        # In production, write to dedicated audit log storage

    # Public API methods expected by tests
    async def add_key(self, user_id: str, provider: str, api_key: str) -> bool:
        """
        Add/store an API key for a user (alias for store_user_key)

        Args:
            user_id: User identifier
            provider: Provider identifier
            api_key: API key to store

        Returns:
            True if stored successfully
        """
        return await self.store_user_key(user_id, provider, api_key)

    async def get_key(self, user_id: str, provider: str) -> Optional[str]:
        """
        Retrieve decrypted API key for user/provider

        Args:
            user_id: User identifier
            provider: Provider identifier

        Returns:
            Decrypted API key or None
        """
        # Check cache first
        if user_id in self._key_cache and provider in self._key_cache[user_id]:
            return self._key_cache[user_id][provider]

        # Load from storage
        import os

        user_file = self.storage_path / f"{user_id}.json"

        if not os.path.exists(user_file):
            return None

        try:
            with open(user_file, "r") as f:
                user_keys = json.load(f)

            if provider not in user_keys:
                return None

            # Decrypt key
            encrypted_key = user_keys[provider]["encrypted_key"].encode()
            decrypted_key: str = self.cipher.decrypt(encrypted_key).decode()

            # Cache it
            if user_id not in self._key_cache:
                self._key_cache[user_id] = {}
            self._key_cache[user_id][provider] = decrypted_key

            return decrypted_key

        except Exception as e:
            logger.error("Failed to retrieve key", user_id=user_id, provider=provider, error=str(e))
            return None

    async def list_user_keys(self, user_id: str) -> List[str]:
        """
        List all providers for which user has stored keys

        Args:
            user_id: User identifier

        Returns:
            List of provider identifiers
        """
        import os

        user_file = self.storage_path / f"{user_id}.json"

        if not os.path.exists(user_file):
            return []

        try:
            with open(user_file, "r") as f:
                user_keys = json.load(f)

            return list(user_keys.keys())

        except Exception as e:
            logger.error("Failed to list keys", user_id=user_id, error=str(e))
            return []

    async def remove_key(self, user_id: str, provider: str) -> bool:
        """
        Remove a stored API key

        Args:
            user_id: User identifier
            provider: Provider identifier

        Returns:
            True if removed successfully
        """
        import os

        user_file = self.storage_path / f"{user_id}.json"

        if not os.path.exists(user_file):
            return False

        try:
            with open(user_file, "r") as f:
                user_keys = json.load(f)

            if provider not in user_keys:
                return False

            # Remove key
            del user_keys[provider]

            # Save
            with open(user_file, "w") as f:
                json.dump(user_keys, f, indent=2)

            # Clear from cache
            if user_id in self._key_cache and provider in self._key_cache[user_id]:
                del self._key_cache[user_id][provider]

            logger.info("Key removed", user_id=user_id, provider=provider)
            await self._audit_log(user_id, f"Removed {provider} key")

            return True

        except Exception as e:
            logger.error("Failed to remove key", user_id=user_id, provider=provider, error=str(e))
            return False
