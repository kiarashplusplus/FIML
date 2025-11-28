"""
Tests for UsageAnalytics - Provider API usage tracking and quota management

Tests cover:
- Redis-based usage tracking
- Daily/monthly counters
- Quota threshold warnings (80%)
- Provider-specific limits
- In-memory fallback when Redis unavailable
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fiml.bot.core.usage_analytics import UsageAnalytics, PROVIDER_LIMITS, QUOTA_WARNING_THRESHOLD


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing (no actual Redis connection)"""
    redis = MagicMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.get = AsyncMock(return_value=b"45")
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def usage_analytics(mock_redis):
    """UsageAnalytics instance with mocked Redis"""
    return UsageAnalytics(redis_client=mock_redis)


@pytest.fixture
def usage_analytics_no_redis():
    """UsageAnalytics instance without Redis (in-memory fallback)"""
    return UsageAnalytics(redis_client=None)


class TestUsageAnalyticsInitialization:
    """Test UsageAnalytics initialization"""

    def test_init_with_redis(self, mock_redis):
        """Test initialization with Redis client"""
        analytics = UsageAnalytics(redis_client=mock_redis)
        assert analytics._redis == mock_redis
        assert isinstance(analytics._in_memory_fallback, dict)

    def test_init_without_redis(self):
        """Test initialization without Redis (fallback mode)"""
        analytics = UsageAnalytics(redis_client=None)
        assert analytics._redis is None
        assert isinstance(analytics._in_memory_fallback, dict)


class TestRedisKeyGeneration:
    """Test Redis key generation"""

    def test_daily_key_format(self, usage_analytics):
        """Test daily Redis key format"""
        with patch('fiml.bot.core.usage_analytics.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 11, 28, 14, 0, 0, tzinfo=UTC)
            
            key = usage_analytics._get_redis_key("user123", "binance", "daily")
            assert key == "usage:user123:binance:2025-11-28"

    def test_monthly_key_format(self, usage_analytics):
        """Test monthly Redis key format"""
        with patch('fiml.bot.core.usage_analytics.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 11, 28, 14, 0, 0, tzinfo=UTC)
            
            key = usage_analytics._get_redis_key("user123", "binance", "monthly")
            assert key == "usage:user123:binance:2025-11"

    def test_invalid_period_type(self, usage_analytics):
        """Test invalid period type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid period_type"):
            usage_analytics._get_redis_key("user123", "binance", "yearly")


class TestTrackCall:
    """Test API call tracking"""

    async def test_track_call_with_redis(self, usage_analytics, mock_redis):
        """Test tracking API call with Redis"""
        mock_redis.get.side_effect = [b"46", b"321"]  # daily, monthly
        
        result = await usage_analytics.track_call("user123", "binance", "api_call")
        
        assert result["tracked"] is True
        assert result["daily_count"] == 46
        assert result["monthly_count"] == 321
        
        # Verify Redis calls
        assert mock_redis.incr.call_count == 2  # daily + monthly
        assert mock_redis.expire.call_count == 2

    async def test_track_call_without_redis(self, usage_analytics_no_redis):
        """Test tracking API call with in-memory fallback"""
        result1 = await usage_analytics_no_redis.track_call("user123", "binance")
        result2 = await usage_analytics_no_redis.track_call("user123", "binance")
        
        assert result1["tracked"] is True
        assert result1["daily_count"] == 1
        assert result1["monthly_count"] == 1
        
        assert result2["daily_count"] == 2
        assert result2["monthly_count"] == 2

    async def test_track_call_redis_error(self, usage_analytics, mock_redis):
        """Test tracking when Redis fails"""
        mock_redis.incr.side_effect = Exception("Redis connection error")
        
        result = await usage_analytics.track_call("user123", "binance")
        
        assert result["tracked"] is False
        assert "error" in result


class TestGetUsage:
    """Test usage retrieval"""

    @pytest.mark.asyncio
    async def test_get_daily_usage_with_redis(self, usage_analytics, mock_redis):
        """Test getting daily usage from Redis"""
        mock_redis.get.return_value = b"45"
        
        usage = await usage_analytics.get_usage("user123", "binance", "daily")
        
        assert usage == 45
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_monthly_usage_with_redis(self, usage_analytics, mock_redis):
        """Test getting monthly usage from Redis"""
        mock_redis.get.return_value = b"320"
        
        usage = await usage_analytics.get_usage("user123", "binance", "monthly")
        
        assert usage == 320

    @pytest.mark.asyncio
    async def test_get_usage_no_data(self, usage_analytics, mock_redis):
        """Test getting usage when no data exists"""
        mock_redis.get.return_value = None
        
        usage = await usage_analytics.get_usage("user123", "binance", "daily")
        
        assert usage == 0

    @pytest.mark.asyncio
    async def test_get_usage_without_redis(self, usage_analytics_no_redis):
        """Test getting usage with in-memory fallback"""
        # Track some calls first
        await usage_analytics_no_redis.track_call("user123", "binance")
        await usage_analytics_no_redis.track_call("user123", "binance")
        
        usage = await usage_analytics_no_redis.get_usage("user123", "binance", "daily")
        
        assert usage == 2


class TestCheckQuota:
    """Test quota checking and warnings"""

    @pytest.mark.asyncio
    async def test_check_quota_below_threshold(self, usage_analytics, mock_redis):
        """Test quota check when usage is below 80% threshold"""
        # binance daily limit is 1200, 45 is 3.75%
        mock_redis.get.side_effect = [b"45", b"320"]  # daily, monthly
        
        result = await usage_analytics.check_quota("user123", "binance")
        
        assert result["warning"] is False
        assert result["exceeded"] is False
        assert result["daily_usage"] == 45
        assert result["daily_limit"] == 1200
        assert result["daily_percentage"] == 3.75

    @pytest.mark.asyncio
    async def test_check_quota_at_warning_threshold(self, usage_analytics, mock_redis):
        """Test quota check at 80% threshold (warning)"""
        # binance daily limit is 1200, 960 is 80%
        mock_redis.get.side_effect = [b"960", b"320"]
        
        result = await usage_analytics.check_quota("user123", "binance")
        
        assert result["warning"] is True
        assert result["exceeded"] is False
        assert result["daily_percentage"] == 80.0

    @pytest.mark.asyncio
    async def test_check_quota_exceeded(self, usage_analytics, mock_redis):
        """Test quota check when limit exceeded"""
        # binance daily limit is 1200
        mock_redis.get.side_effect = [b"1250", b"320"]
        
        result = await usage_analytics.check_quota("user123", "binance")
        
        assert result["warning"] is True
        assert result["exceeded"] is True
        assert result["daily_usage"] == 1250

    @pytest.mark.asyncio
    async def test_check_quota_monthly_warning(self, usage_analytics, mock_redis):
        """Test quota warning triggered by monthly usage"""
        # Daily OK (45/1200 = 3.75%), Monthly at warning (29000/36000 = 80.5%)
        mock_redis.get.side_effect = [b"45", b"29000"]
        
        result = await usage_analytics.check_quota("user123", "binance")
        
        assert result["warning"] is True  # Monthly triggers warning
        assert result["monthly_percentage"] > 80.0


class TestGetAllUsage:
    """Test comprehensive usage statistics"""

    @pytest.mark.asyncio
    async def test_get_all_usage_multiple_providers(self, usage_analytics, mock_redis):
        """Test getting usage for all providers"""
        # Mock Redis to return different values for different providers
        call_count = 0
        def mock_get_side_effect(key):
            nonlocal call_count
            # Return usage for binance and alphavantage, 0 for others
            if "binance" in key:
                call_count += 1
                return b"45" if call_count % 2 == 1 else b"320"
            elif "alphavantage" in key:
                call_count += 1
                return b"420" if call_count % 2 == 1 else b"12000"
            return b"0"
        
        mock_redis.get.side_effect = mock_get_side_effect
        
        result = await usage_analytics.get_all_usage("user123")
        
        assert result["total_calls_today"] > 0
        assert len(result["stats"]) >= 2  # At least binance and alphavantage
        assert result["has_warnings"] is True  # alphavantage at 84%
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_all_usage_no_usage(self, usage_analytics, mock_redis):
        """Test getting usage when no providers have been used"""
        mock_redis.get.return_value = b"0"
        
        result = await usage_analytics.get_all_usage("user123")
        
        assert result["stats"] == []
        assert result["total_calls_today"] == 0
        assert result["has_warnings"] is False

    @pytest.mark.asyncio
    async def test_get_all_usage_sorted_by_usage(self, usage_analytics, mock_redis):
        """Test that results are sorted by daily usage (descending)"""
        call_count = 0
        def mock_get_side_effect(key):
            nonlocal call_count
            call_count += 1
            if "alphavantage" in key:
                return b"420" if call_count % 2 == 1 else b"12000"
            elif "binance" in key:
                return b"45" if call_count % 2 == 1 else b"320"
            return b"0"
        
        mock_redis.get.side_effect = mock_get_side_effect
        
        result = await usage_analytics.get_all_usage("user123")
        
        # alphavantage (420) should be before binance (45)
        if len(result["stats"]) >= 2:
            assert result["stats"][0]["daily_usage"] >= result["stats"][1]["daily_usage"]


class TestProviderLimits:
    """Test provider limit configuration"""

    def test_get_provider_limits_known_provider(self, usage_analytics):
        """Test getting limits for known provider"""
        limits = usage_analytics.get_provider_limits("binance")
        
        assert limits["daily"] == 1200
        assert limits["monthly"] == 36000
        assert limits["tier"] == "free"

    def test_get_provider_limits_unknown_provider(self, usage_analytics):
        """Test getting limits for unknown provider (defaults)"""
        limits = usage_analytics.get_provider_limits("unknown_provider")
        
        assert limits["daily"] == 1000
        assert limits["monthly"] == 30000
        assert limits["tier"] == "unknown"

    def test_provider_limits_constant(self):
        """Test PROVIDER_LIMITS constant has expected providers"""
        assert "alphavantage" in PROVIDER_LIMITS
        assert "fmp" in PROVIDER_LIMITS
        assert "finnhub" in PROVIDER_LIMITS
        assert "polygon" in PROVIDER_LIMITS
        assert "binance" in PROVIDER_LIMITS
        assert "coinbase" in PROVIDER_LIMITS
        assert "yfinance" in PROVIDER_LIMITS
        
        # Check yfinance has unlimited quota
        assert PROVIDER_LIMITS["yfinance"]["daily"] == float('inf')


class TestResetUsage:
    """Test usage counter reset"""

    @pytest.mark.asyncio
    async def test_reset_single_provider(self, usage_analytics, mock_redis):
        """Test resetting usage for single provider"""
        result = await usage_analytics.reset_usage("user123", "binance", "daily")
        
        assert result["reset"] is True
        assert result["providers_reset"] == 1
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_all_providers(self, usage_analytics, mock_redis):
        """Test resetting usage for all providers"""
        result = await usage_analytics.reset_usage("user123", provider=None, period_type="daily")
        
        assert result["reset"] is True
        assert result["providers_reset"] == len(PROVIDER_LIMITS)
        assert mock_redis.delete.call_count == len(PROVIDER_LIMITS)

    @pytest.mark.asyncio
    async def test_reset_monthly_usage(self, usage_analytics, mock_redis):
        """Test resetting monthly usage"""
        result = await usage_analytics.reset_usage("user123", "binance", "monthly")
        
        assert result["reset"] is True
        # Verify the key contains the month
        call_args = mock_redis.delete.call_args[0][0]
        assert "2025-11" in call_args  # Current month

    @pytest.mark.asyncio
    async def test_reset_without_redis(self, usage_analytics_no_redis):
        """Test resetting with in-memory fallback"""
        # Track some usage first
        await usage_analytics_no_redis.track_call("user123", "binance")
        
        # Reset
        result = await usage_analytics_no_redis.reset_usage("user123", "binance", "daily")
        
        assert result["reset"] is True
        
        # Verify usage is now 0
        usage = await usage_analytics_no_redis.get_usage("user123", "binance", "daily")
        assert usage == 0


class TestQuotaWarningThreshold:
    """Test quota warning threshold constant"""

    def test_quota_warning_threshold_value(self):
        """Test that warning threshold is 80%"""
        assert QUOTA_WARNING_THRESHOLD == 0.8

    @pytest.mark.asyncio
    async def test_warning_triggers_at_threshold(self, usage_analytics, mock_redis):
        """Test that warning triggers exactly at 80%"""
        # Set usage to exactly 80% of limit (1200 * 0.8 = 960)
        mock_redis.get.side_effect = [b"960", b"100"]
        
        result = await usage_analytics.check_quota("user123", "binance")
        
        assert result["warning"] is True
        assert result["daily_percentage"] == 80.0
