"""
Component 1: User Provider Key Manager
Handles collection, validation, and secure storage of user API keys (BYOK model)
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional

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
        Initialize key manager

        Args:
            encryption_key: Fernet encryption key (generated if not provided)
            storage_path: Path to store encrypted keys
        """
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.storage_path = storage_path

        # In-memory cache for decrypted keys (session-scoped)
        self._key_cache: Dict[str, Dict[str, str]] = {}

        # Quota tracking (in-memory for now, should be Redis in production)
        self._quota_usage: Dict[str, Dict[str, int]] = {}

        logger.info("UserProviderKeyManager initialized", storage_path=storage_path)

    def get_provider_info(self, provider: str) -> Optional[Dict]:
        """Get information about a provider for user guidance"""
        return self.PROVIDER_INFO.get(provider)

    def list_supported_providers(self) -> List[Dict]:
        """List all supported providers with their information"""
        return [
            {"id": key, **value}
            for key, value in self.PROVIDER_INFO.items()
        ]

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
        logger.info(
            "Key format validation",
            provider=provider,
            valid=is_valid,
            key_length=len(api_key)
        )
        return is_valid

    async def test_provider_key(self, provider: str, api_key: str) -> Dict:
        """
        Test API key by making actual API call

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
                    "message": f"Provider {provider} not yet supported for testing"
                }
        except Exception as e:
            logger.error("Key test failed", provider=provider, error=str(e))
            return {
                "valid": False,
                "tier": "unknown",
                "message": f"Test failed: {str(e)}"
            }

    async def _test_alpha_vantage(self, api_key: str) -> Dict:
        """Test Alpha Vantage API key"""
        import aiohttp

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": "IBM",
            "interval": "5min",
            "apikey": api_key
        }

        async with aiohttp.ClientSession() as session, session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()

            if "Error Message" in data:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Invalid API key"
                }
            elif "Note" in data:
                # Rate limit message
                return {
                    "valid": True,
                    "tier": "free",
                    "message": "Free tier (5 requests/minute, 500/day)"
                }
            elif "Time Series (5min)" in data:
                return {
                    "valid": True,
                    "tier": "free",
                    "message": "Free tier (5 requests/minute, 500/day)"
                }
            else:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Unexpected response from API"
                }

    async def _test_polygon(self, api_key: str) -> Dict:
        """Test Polygon.io API key"""
        import aiohttp

        url = "https://api.polygon.io/v2/aggs/ticker/AAPL/prev"
        headers = {"Authorization": f"Bearer {api_key}"}

        async with aiohttp.ClientSession() as session, session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                return {
                    "valid": True,
                    "tier": "paid",
                    "message": "Polygon.io key validated"
                }
            elif resp.status == 401:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Invalid API key"
                }
            else:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": f"API returned status {resp.status}"
                }

    async def _test_finnhub(self, api_key: str) -> Dict:
        """Test Finnhub API key"""
        import aiohttp

        url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}"

        async with aiohttp.ClientSession() as session, session.get(url, timeout=10) as resp:
            data = await resp.json()

            if "error" in data:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Invalid API key"
                }
            elif "c" in data:  # Current price
                return {
                    "valid": True,
                    "tier": "free",
                    "message": "Free tier (60 requests/minute)"
                }
            else:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Unexpected response"
                }

    async def _test_fmp(self, api_key: str) -> Dict:
        """Test Financial Modeling Prep API key"""
        import aiohttp

        url = f"https://financialmodelingprep.com/api/v3/quote/AAPL?apikey={api_key}"

        async with aiohttp.ClientSession() as session, session.get(url, timeout=10) as resp:
            data = await resp.json()

            if isinstance(data, dict) and "Error Message" in data:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Invalid API key"
                }
            elif isinstance(data, list) and len(data) > 0:
                return {
                    "valid": True,
                    "tier": "free",
                    "message": "Free tier (250 requests/day)"
                }
            else:
                return {
                    "valid": False,
                    "tier": "unknown",
                    "message": "Unexpected response"
                }

    async def store_user_key(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Encrypt and store user API key

        Args:
            user_id: User identifier
            provider: Provider identifier
            api_key: API key to store
            metadata: Optional metadata (tier, limits, etc.)

        Returns:
            True if stored successfully
        """
        try:
            # Encrypt the key
            encrypted_key = self.cipher.encrypt(api_key.encode())

            # Prepare storage object
            key_data = {
                "provider": provider,
                "encrypted_key": encrypted_key.decode(),
                "added_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            # Store (simplified - in production use AWS Secrets Manager or similar)
            import os
            os.makedirs(self.storage_path, exist_ok=True)

            user_file = f"{self.storage_path}/{user_id}.json"

            # Load existing keys
            if os.path.exists(user_file):
                with open(user_file, "r") as f:
                    user_keys = json.load(f)
            else:
                user_keys = {}

            # Add new key
            user_keys[provider] = key_data

            # Save
            with open(user_file, "w") as f:
                json.dump(user_keys, f, indent=2)

            # Update cache
            if user_id not in self._key_cache:
                self._key_cache[user_id] = {}
            self._key_cache[user_id][provider] = api_key

            logger.info(
                "User key stored",
                user_id=user_id,
                provider=provider,
                has_metadata=bool(metadata)
            )

            # Audit log
            await self._audit_log(user_id, f"Added {provider} key")

            return True

        except Exception as e:
            logger.error("Failed to store key", user_id=user_id, provider=provider, error=str(e))
            return False

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

        # Load from storage
        user_file = f"{self.storage_path}/{user_id}.json"

        try:
            import os
            if not os.path.exists(user_file):
                return {}

            with open(user_file, "r") as f:
                user_keys_data = json.load(f)

            # Decrypt keys
            decrypted_keys = {}
            for provider, key_data in user_keys_data.items():
                encrypted_key = key_data["encrypted_key"].encode()
                decrypted_key = self.cipher.decrypt(encrypted_key).decode()
                decrypted_keys[provider] = decrypted_key

            # Update cache
            self._key_cache[user_id] = decrypted_keys.copy()

            return decrypted_keys

        except Exception as e:
            logger.error("Failed to retrieve keys", user_id=user_id, error=str(e))
            return {}

    async def remove_user_key(self, user_id: str, provider: str) -> bool:
        """
        Remove a user's API key for a provider

        Args:
            user_id: User identifier
            provider: Provider to remove

        Returns:
            True if removed successfully
        """
        try:
            user_file = f"{self.storage_path}/{user_id}.json"

            import os
            if not os.path.exists(user_file):
                return False

            with open(user_file, "r") as f:
                user_keys = json.load(f)

            if provider not in user_keys:
                return False

            # Remove key
            del user_keys[provider]

            # Save
            with open(user_file, "w") as f:
                json.dump(user_keys, f, indent=2)

            # Update cache
            if user_id in self._key_cache and provider in self._key_cache[user_id]:
                del self._key_cache[user_id][provider]

            logger.info("User key removed", user_id=user_id, provider=provider)

            # Audit log
            await self._audit_log(user_id, f"Removed {provider} key")

            return True

        except Exception as e:
            logger.error("Failed to remove key", user_id=user_id, provider=provider, error=str(e))
            return False

    async def list_user_providers(self, user_id: str) -> List[Dict]:
        """
        List all providers user has keys for

        Args:
            user_id: User identifier

        Returns:
            List of provider info dicts
        """
        user_file = f"{self.storage_path}/{user_id}.json"

        try:
            import os
            if not os.path.exists(user_file):
                return []

            with open(user_file, "r") as f:
                user_keys_data = json.load(f)

            providers = []
            for provider, key_data in user_keys_data.items():
                provider_info = self.PROVIDER_INFO.get(provider, {})
                providers.append({
                    "provider": provider,
                    "name": provider_info.get("name", provider),
                    "added_at": key_data.get("added_at"),
                    "metadata": key_data.get("metadata", {}),
                })

            return providers

        except Exception as e:
            logger.error("Failed to list providers", user_id=user_id, error=str(e))
            return []

    async def track_usage(self, user_id: str, provider: str):
        """
        Track API usage for quota management

        Args:
            user_id: User identifier
            provider: Provider used
        """
        # In-memory tracking (should be Redis in production)
        today = datetime.utcnow().strftime("%Y-%m-%d")
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
                "Quota warning",
                user_id=user_id,
                provider=provider,
                usage=usage,
                limit=limit
            )
            return {"warning": True, "usage": usage, "limit": limit}

        return {"warning": False, "usage": usage, "limit": limit}

    async def get_usage(self, user_id: str, provider: str) -> int:
        """Get current usage for user/provider"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"{user_id}:{provider}:{today}"
        return self._quota_usage.get(key, 0)

    async def _audit_log(self, user_id: str, action: str):
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
            timestamp=datetime.utcnow().isoformat()
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
        user_file = f"{self.storage_path}/{user_id}.json"

        if not os.path.exists(user_file):
            return None

        try:
            with open(user_file, "r") as f:
                user_keys = json.load(f)

            if provider not in user_keys:
                return None

            # Decrypt key
            encrypted_key = user_keys[provider]["encrypted_key"].encode()
            decrypted_key = self.cipher.decrypt(encrypted_key).decode()

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
        user_file = f"{self.storage_path}/{user_id}.json"

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
        user_file = f"{self.storage_path}/{user_id}.json"

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
