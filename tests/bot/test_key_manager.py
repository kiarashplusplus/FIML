"""
Tests for UserProviderKeyManager (Component 1)
"""


import json

import pytest

from fiml.bot.core.key_manager import UserProviderKeyManager


class TestUserProviderKeyManager:
    """Test API key management with encryption"""

    @pytest.fixture
    def key_manager(self, tmp_path):
        """Create a key manager with temporary storage"""
        storage_path = tmp_path / "keys"
        return UserProviderKeyManager(storage_path=str(storage_path))

    async def test_key_validation_alpha_vantage(self, key_manager):
        """Test Alpha Vantage key format validation"""
        # Valid format (16 uppercase alphanumeric)
        result = key_manager.validate_key_format("alpha_vantage", "ABC123XYZ4567890")
        assert result is True

        # Invalid format
        result_invalid = key_manager.validate_key_format("alpha_vantage", "too_short")
        assert result_invalid is False

    async def test_key_validation_polygon(self, key_manager):
        """Test Polygon.io key format validation"""
        # Valid format (32 alphanumeric with dash/underscore)
        # Pattern is: ^[A-Za-z0-9_-]{32}$
        valid_key = "abcd1234EFGH5678ijkl9012MNOP3456"  # exactly 32 chars
        result = key_manager.validate_key_format("polygon", valid_key)
        assert result is True

    async def test_key_validation_finnhub(self, key_manager):
        """Test Finnhub key format validation"""
        # Valid format (20 lowercase alphanumeric)
        valid_key = "abcdefgh12345678ijkl"
        result = key_manager.validate_key_format("finnhub", valid_key)
        assert result is True

    async def test_key_validation_fmp(self, key_manager):
        """Test FMP key format validation"""
        # Valid format (32 lowercase alphanumeric)
        valid_key = "abcdefgh12345678ijklmnop90123456"
        result = key_manager.validate_key_format("fmp", valid_key)
        assert result is True

    async def test_key_validation_unknown_provider(self, key_manager):
        """Test validation for unknown provider (should allow any format)"""
        result = key_manager.validate_key_format("unknown_provider", "any_key_format")
        assert result is True

    async def test_add_and_retrieve_key(self, key_manager):
        """Test adding and retrieving encrypted keys"""
        user_id = "test_user_123"
        provider = "alpha_vantage"
        api_key = "TEST_KEY_123456789"

        # Add key
        success = await key_manager.add_key(user_id, provider, api_key)
        assert success

        # Retrieve key
        retrieved = await key_manager.get_key(user_id, provider)
        assert retrieved == api_key

    async def test_list_user_keys(self, key_manager):
        """Test listing all keys for a user"""
        user_id = "test_user_456"

        # Add multiple keys
        await key_manager.add_key(user_id, "alpha_vantage", "KEY1")
        await key_manager.add_key(user_id, "polygon", "KEY2")

        # List keys
        keys = await key_manager.list_user_keys(user_id)
        assert len(keys) == 2
        assert "alpha_vantage" in keys
        assert "polygon" in keys

    async def test_remove_key(self, key_manager):
        """Test removing a key"""
        user_id = "test_user_789"
        provider = "finnhub"

        # Add then remove
        await key_manager.add_key(user_id, provider, "TEST_KEY")
        assert await key_manager.get_key(user_id, provider) is not None

        await key_manager.remove_key(user_id, provider)
        assert await key_manager.get_key(user_id, provider) is None

    async def test_key_encryption(self, key_manager):
        """Test that keys are encrypted at rest"""
        user_id = "test_user_encrypt"
        provider = "alpha_vantage"
        api_key = "SENSITIVE_KEY_123"

        await key_manager.add_key(user_id, provider, api_key)

        # Read raw storage (should be encrypted)
        storage_file = key_manager.storage_path / f"{user_id}.json"
        with open(storage_file, 'r') as f:
            data = json.load(f)

        # Encrypted key should not match plaintext
        assert data.get(provider) != api_key
        assert data.get(provider) != ""

    async def test_get_provider_info(self, key_manager):
        """Test getting provider information"""
        info = key_manager.get_provider_info("alpha_vantage")

        assert info is not None
        assert info["name"] == "Alpha Vantage"
        assert info["free_tier"] is True
        assert "signup_url" in info

    async def test_get_provider_info_unknown(self, key_manager):
        """Test getting info for unknown provider"""
        info = key_manager.get_provider_info("unknown_provider")
        assert info is None

    async def test_list_supported_providers(self, key_manager):
        """Test listing all supported providers"""
        providers = key_manager.list_supported_providers()

        assert len(providers) >= 4
        provider_ids = [p["id"] for p in providers]
        assert "alpha_vantage" in provider_ids
        assert "polygon" in provider_ids
        assert "finnhub" in provider_ids
        assert "fmp" in provider_ids

    async def test_store_user_key_with_metadata(self, key_manager):
        """Test storing key with metadata"""
        user_id = "test_user_meta"
        provider = "alpha_vantage"
        api_key = "META_TEST_KEY_123"
        metadata = {"tier": "free", "limit": "500/day"}

        success = await key_manager.store_user_key(user_id, provider, api_key, metadata)
        assert success

        # Check metadata is stored
        providers = await key_manager.list_user_providers(user_id)
        assert len(providers) == 1
        assert providers[0]["metadata"]["tier"] == "free"

    async def test_list_user_providers(self, key_manager):
        """Test listing user providers with full info"""
        user_id = "test_user_providers"

        await key_manager.store_user_key(
            user_id, "alpha_vantage", "KEY1", {"tier": "free"}
        )
        await key_manager.store_user_key(
            user_id, "polygon", "KEY2", {"tier": "paid"}
        )

        providers = await key_manager.list_user_providers(user_id)

        assert len(providers) == 2
        assert any(p["provider"] == "alpha_vantage" for p in providers)
        assert any(p["provider"] == "polygon" for p in providers)

    async def test_list_user_providers_empty(self, key_manager):
        """Test listing providers for user with no keys"""
        providers = await key_manager.list_user_providers("nonexistent_user")
        assert providers == []

    async def test_get_user_keys(self, key_manager):
        """Test getting all user keys as dict"""
        user_id = "test_user_getkeys"

        await key_manager.add_key(user_id, "alpha_vantage", "KEY_AV")
        await key_manager.add_key(user_id, "finnhub", "KEY_FH")

        keys = await key_manager.get_user_keys(user_id)

        assert len(keys) == 2
        assert keys["alpha_vantage"] == "KEY_AV"
        assert keys["finnhub"] == "KEY_FH"

    async def test_get_user_keys_empty(self, key_manager):
        """Test getting keys for user with no stored keys"""
        keys = await key_manager.get_user_keys("nonexistent_user")
        assert keys == {}

    async def test_remove_user_key(self, key_manager):
        """Test removing user key via remove_user_key"""
        user_id = "test_remove_key"
        provider = "alpha_vantage"

        await key_manager.add_key(user_id, provider, "TEST_KEY")

        success = await key_manager.remove_user_key(user_id, provider)
        assert success

        # Key should be gone
        key = await key_manager.get_key(user_id, provider)
        assert key is None

    async def test_remove_nonexistent_key(self, key_manager):
        """Test removing key that doesn't exist"""
        result = await key_manager.remove_key("no_user", "no_provider")
        assert result is False

    async def test_track_usage(self, key_manager):
        """Test tracking API usage"""
        user_id = "test_usage"
        provider = "alpha_vantage"

        # Track multiple usages
        result1 = await key_manager.track_usage(user_id, provider)
        result2 = await key_manager.track_usage(user_id, provider)

        # Usage should be tracked
        assert result1["usage"] < result2["usage"]

    async def test_get_usage(self, key_manager):
        """Test getting current usage"""
        user_id = "test_get_usage"
        provider = "alpha_vantage"

        # Initial usage should be 0
        usage = await key_manager.get_usage(user_id, provider)
        assert usage == 0

        # After tracking
        await key_manager.track_usage(user_id, provider)
        usage = await key_manager.get_usage(user_id, provider)
        assert usage == 1

    async def test_key_caching(self, key_manager):
        """Test that keys are cached in memory"""
        user_id = "test_cache"
        provider = "alpha_vantage"
        api_key = "CACHED_KEY_123"

        await key_manager.add_key(user_id, provider, api_key)

        # Key should be in cache
        assert user_id in key_manager._key_cache
        assert key_manager._key_cache[user_id][provider] == api_key

    async def test_custom_encryption_key(self, tmp_path):
        """Test using custom encryption key"""
        from cryptography.fernet import Fernet

        custom_key = Fernet.generate_key()
        storage_path = tmp_path / "custom_keys"

        km = UserProviderKeyManager(
            encryption_key=custom_key,
            storage_path=str(storage_path)
        )

        user_id = "custom_key_user"
        api_key = "MY_SECRET_KEY"

        await km.add_key(user_id, "alpha_vantage", api_key)
        retrieved = await km.get_key(user_id, "alpha_vantage")

        assert retrieved == api_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

