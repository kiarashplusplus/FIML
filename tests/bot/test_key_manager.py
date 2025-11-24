"""
Tests for UserProviderKeyManager (Component 1)
"""

import pytest
from pathlib import Path
from fiml.bot.core.key_manager import UserProviderKeyManager


class TestUserProviderKeyManager:
    """Test API key management with encryption"""
    
    @pytest.fixture
    def key_manager(self, tmp_path):
        """Create a key manager with temporary storage"""
        storage_path = tmp_path / "keys"
        return UserProviderKeyManager(storage_path=str(storage_path))
    
    def test_key_validation_alpha_vantage(self, key_manager):
        """Test Alpha Vantage key format validation"""
        # Valid format
        result = key_manager.validate_key_format("alpha_vantage", "ABC123XYZ456789")
        assert result.is_valid
        assert result.tier == "free"
        
        # Invalid format (too short)
        result = key_manager.validate_key_format("alpha_vantage", "SHORT")
        assert not result.is_valid
        assert "Invalid format" in result.message
    
    def test_key_validation_polygon(self, key_manager):
        """Test Polygon.io key format validation"""
        result = key_manager.validate_key_format("polygon", "ABC123XYZ456789012345678901234")
        assert result.is_valid
        assert result.tier == "paid"
    
    def test_add_and_retrieve_key(self, key_manager):
        """Test adding and retrieving encrypted keys"""
        user_id = "test_user_123"
        provider = "alpha_vantage"
        api_key = "TEST_KEY_123456789"
        
        # Add key
        success = key_manager.add_key(user_id, provider, api_key)
        assert success
        
        # Retrieve key
        retrieved = key_manager.get_key(user_id, provider)
        assert retrieved == api_key
    
    def test_list_user_keys(self, key_manager):
        """Test listing all keys for a user"""
        user_id = "test_user_456"
        
        # Add multiple keys
        key_manager.add_key(user_id, "alpha_vantage", "KEY1")
        key_manager.add_key(user_id, "polygon", "KEY2")
        
        # List keys
        keys = key_manager.list_user_keys(user_id)
        assert len(keys) == 2
        assert "alpha_vantage" in keys
        assert "polygon" in keys
    
    def test_remove_key(self, key_manager):
        """Test removing a key"""
        user_id = "test_user_789"
        provider = "finnhub"
        
        # Add then remove
        key_manager.add_key(user_id, provider, "TEST_KEY")
        assert key_manager.get_key(user_id, provider) is not None
        
        key_manager.remove_key(user_id, provider)
        assert key_manager.get_key(user_id, provider) is None
    
    def test_key_encryption(self, key_manager):
        """Test that keys are encrypted at rest"""
        user_id = "test_user_encrypt"
        provider = "alpha_vantage"
        api_key = "SENSITIVE_KEY_123"
        
        key_manager.add_key(user_id, provider, api_key)
        
        # Read raw storage (should be encrypted)
        import json
        storage_file = key_manager.storage_path / f"{user_id}.json"
        with open(storage_file, 'r') as f:
            data = json.load(f)
        
        # Encrypted key should not match plaintext
        assert data.get(provider) != api_key
        assert data.get(provider) != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
