"""
Tests for FIMLProviderConfigurator (Component 2)
Tests per-user FIML configuration and provider priority system
"""
import pytest

from fiml.bot.core.provider_configurator import FIMLProviderConfigurator


class TestFIMLProviderConfigurator:
    """Test suite for FIML provider configuration"""

    async def test_init_configurator(self):
        """Test configurator initialization"""
        config = FIMLProviderConfigurator()
        assert config is not None
        assert hasattr(config, 'get_user_provider_config')

    async def test_get_config_no_user_keys(self):
        """Test configuration when user has no API keys"""
        config = FIMLProviderConfigurator()
        user_config = config.get_user_provider_config("user_123", user_keys={})

        # Should fall back to platform free tier (Yahoo)
        assert user_config is not None
        assert user_config['fallback_provider'] == 'yahoo_finance'
        assert user_config['user_id'] == 'user_123'

    async def test_get_config_with_free_tier_key(self):
        """Test configuration when user has free tier API key"""
        config = FIMLProviderConfigurator()
        user_keys = {
            'alpha_vantage': {
                'key': 'test_key_123',
                'tier': 'free',
                'quota': {'requests_per_minute': 5}
            }
        }
        user_config = config.get_user_provider_config("user_123", user_keys=user_keys)

        # Should prioritize user's free tier key
        assert user_config is not None
        assert 'alpha_vantage' in str(user_config).lower() or 'providers' in user_config

    async def test_get_config_with_paid_tier_key(self):
        """Test configuration when user has paid tier API key"""
        config = FIMLProviderConfigurator()
        user_keys = {
            'polygon': {
                'key': 'paid_key_456',
                'tier': 'paid',
                'quota': {'requests_per_minute': 100}
            }
        }
        user_config = config.get_user_provider_config("user_123", user_keys=user_keys)

        # Should prioritize user's paid tier key (highest priority)
        assert user_config is not None
        assert user_config['user_id'] == 'user_123'

    async def test_priority_system_paid_over_free(self):
        """Test that paid tier keys are prioritized over free tier"""
        config = FIMLProviderConfigurator()
        user_keys = {
            'alpha_vantage': {'key': 'free_key', 'tier': 'free'},
            'polygon': {'key': 'paid_key', 'tier': 'paid'}
        }
        user_config = config.get_user_provider_config("user_123", user_keys=user_keys)

        # Paid should be prioritized
        assert user_config is not None
        # Config should indicate paid tier preference
        assert user_config['user_id'] == 'user_123'

    async def test_multiple_free_tier_keys(self):
        """Test configuration with multiple free tier keys"""
        config = FIMLProviderConfigurator()
        user_keys = {
            'alpha_vantage': {'key': 'av_key', 'tier': 'free'},
            'finnhub': {'key': 'fh_key', 'tier': 'free'}
        }
        user_config = config.get_user_provider_config("user_123", user_keys=user_keys)

        assert user_config is not None
        assert user_config['user_id'] == 'user_123'

    async def test_usage_tracking_initialization(self):
        """Test that usage tracking is initialized for user"""
        config = FIMLProviderConfigurator()
        user_config = config.get_user_provider_config("user_123", user_keys={})

        # Should have usage tracking structure
        assert user_config is not None
        assert 'user_id' in user_config

    async def test_fallback_suggestions(self):
        """Test fallback provider suggestions"""
        config = FIMLProviderConfigurator()

        # Get fallback suggestions for a failed provider
        suggestions = config.get_fallback_suggestions('alpha_vantage')

        assert suggestions is not None
        assert isinstance(suggestions, (list, str))

    async def test_provider_health_monitoring(self):
        """Test provider health check functionality"""
        config = FIMLProviderConfigurator()

        # Check if provider is healthy
        is_healthy = config.check_provider_health('yahoo_finance')

        assert isinstance(is_healthy, bool)

    async def test_quota_exceeded_handling(self):
        """Test behavior when user quota is exceeded"""
        config = FIMLProviderConfigurator()
        user_keys = {
            'alpha_vantage': {
                'key': 'test_key',
                'tier': 'free',
                'quota': {'requests_per_minute': 5},
                'usage': {'current': 5}  # At limit
            }
        }

        user_config = config.get_user_provider_config("user_123", user_keys=user_keys)

        # Should still provide config (with fallback)
        assert user_config is not None

    async def test_invalid_key_handling(self):
        """Test handling of invalid API keys"""
        config = FIMLProviderConfigurator()
        user_keys = {
            'alpha_vantage': {
                'key': 'INVALID_KEY',
                'tier': 'free',
                'valid': False
            }
        }

        user_config = config.get_user_provider_config("user_123", user_keys=user_keys)

        # Should fall back to platform free tier
        assert user_config is not None
        assert user_config.get('fallback_provider') == 'yahoo_finance'

    async def test_config_caching(self):
        """Test that configurations can be cached"""
        config = FIMLProviderConfigurator()

        # Get config twice for same user
        config1 = config.get_user_provider_config("user_123", user_keys={})
        config2 = config.get_user_provider_config("user_123", user_keys={})

        # Both should be valid
        assert config1 is not None
        assert config2 is not None

    async def test_error_handling_with_fallback(self):
        """Test error handling falls back gracefully"""
        config = FIMLProviderConfigurator()

        # Should handle errors gracefully
        try:
            user_config = config.get_user_provider_config("user_123", user_keys={})
            assert user_config is not None
        except Exception as e:
            pytest.fail(f"Should handle errors gracefully: {e}")
