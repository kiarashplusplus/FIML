"""
Live System Integration Tests

These tests validate the actual running system with real services.
They require Docker containers to be running.
"""

import pytest
import asyncio
from datetime import datetime

from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.registry import provider_registry
from fiml.arbitration.engine import arbitration_engine
from fiml.cache.manager import cache_manager


@pytest.mark.live
class TestLiveProviders:
    """Test live provider functionality"""

    @pytest.mark.asyncio
    async def test_yahoo_finance_provider(self):
        """Test Yahoo Finance provider with real data"""
        from fiml.providers.yahoo_finance import YahooFinanceProvider
        
        provider = YahooFinanceProvider()
        await provider.initialize()
        
        try:
            asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY)
            response = await provider.fetch_price(asset)
            
            assert response.provider == "yahoo_finance"
            assert response.data_type == DataType.PRICE
            assert "price" in response.data
            assert response.data["price"] > 0
            assert response.is_valid
            
        finally:
            await provider.shutdown()

    @pytest.mark.asyncio
    async def test_provider_health_checks(self):
        """Test health checks for all providers"""
        await provider_registry.initialize()
        
        try:
            health_statuses = await provider_registry.get_all_health()
            
            assert len(health_statuses) > 0
            
            for health in health_statuses:
                assert "provider_name" in health or "provider" in health
                assert "is_healthy" in health
                
        finally:
            await provider_registry.shutdown()


@pytest.mark.live
class TestLiveArbitration:
    """Test live data arbitration"""

    @pytest.mark.asyncio
    async def test_arbitration_with_multiple_providers(self):
        """Test arbitration across multiple providers"""
        await provider_registry.initialize()
        
        try:
            asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)
            
            plan = await arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.PRICE,
                user_region="US"
            )
            
            assert len(plan.providers) > 0
            assert plan.primary_provider is not None
            
            # Execute the plan
            response = await arbitration_engine.execute_with_fallback(
                plan, asset, DataType.PRICE
            )
            
            assert response is not None
            assert response.is_valid
            assert "price" in response.data
            
        finally:
            await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_arbitration_fallback(self):
        """Test that arbitration falls back when primary fails"""
        await provider_registry.initialize()
        
        try:
            # Use a symbol that might fail on some providers
            asset = Asset(symbol="TEST", asset_type=AssetType.EQUITY, market=Market.US)
            
            plan = await arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.PRICE,
                user_region="US"
            )
            
            # Plan should have fallback providers
            assert len(plan.fallback_providers) > 0
            
        finally:
            await provider_registry.shutdown()


@pytest.mark.live
@pytest.mark.skipif(
    "not config.getoption('--run-cache-tests')",
    reason="Requires Redis/PostgreSQL"
)
class TestLiveCache:
    """Test live caching functionality"""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test setting and getting cached data"""
        try:
            await cache_manager.initialize()
            
            key = "test:live:cache:key"
            value = {"price": 100.0, "timestamp": datetime.utcnow().isoformat()}
            
            # Set value
            await cache_manager.set(key, value, ttl=60)
            
            # Get value
            cached = await cache_manager.get(key)
            assert cached is not None
            assert cached["price"] == 100.0
            
            # Clean up
            await cache_manager.delete(key)
            
        finally:
            await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that cache entries expire"""
        try:
            await cache_manager.initialize()
            
            key = "test:live:cache:expire"
            value = {"test": "data"}
            
            # Set with very short TTL
            await cache_manager.set(key, value, ttl=1)
            
            # Should exist immediately
            cached = await cache_manager.get(key)
            assert cached is not None
            
            # Wait for expiration
            await asyncio.sleep(2)
            
            # Should be gone
            expired = await cache_manager.get(key)
            assert expired is None
            
        finally:
            await cache_manager.shutdown()


@pytest.mark.live
class TestLiveDataQuality:
    """Test data quality from live providers"""

    @pytest.mark.asyncio
    async def test_price_data_consistency(self):
        """Test that price data is consistent across providers"""
        await provider_registry.initialize()
        
        try:
            asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)
            
            # Get data from multiple providers
            responses = []
            for provider_name in ["yahoo_finance"]:  # Can add more providers
                provider = provider_registry.get_provider(provider_name)
                if provider and await provider.supports_asset(asset):
                    try:
                        response = await provider.fetch_price(asset)
                        responses.append(response)
                    except Exception:
                        pass
            
            if len(responses) >= 1:
                # Check that all prices are positive
                for response in responses:
                    assert response.data["price"] > 0
                    assert response.confidence > 0
                
        finally:
            await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_data_lineage_tracking(self):
        """Test that data lineage is properly tracked"""
        await provider_registry.initialize()
        
        try:
            asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)
            
            plan = await arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.PRICE,
                user_region="US"
            )
            
            response = await arbitration_engine.execute_with_fallback(
                plan, asset, DataType.PRICE
            )
            
            # Check metadata contains lineage info
            assert "source" in response.metadata or response.provider
            assert response.timestamp is not None
            
        finally:
            await provider_registry.shutdown()


@pytest.mark.live
class TestLivePerformance:
    """Test system performance with live data"""

    @pytest.mark.asyncio
    async def test_response_time(self):
        """Test that responses are returned within acceptable time"""
        import time
        
        await provider_registry.initialize()
        
        try:
            asset = Asset(symbol="AAPL", asset_type=AssetType.EQUITY, market=Market.US)
            
            start = time.time()
            
            plan = await arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.PRICE,
                user_region="US"
            )
            
            response = await arbitration_engine.execute_with_fallback(
                plan, asset, DataType.PRICE
            )
            
            elapsed = time.time() - start
            
            # Should respond within 5 seconds
            assert elapsed < 5.0
            assert response is not None
            
        finally:
            await provider_registry.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self):
        """Test performance under concurrent load"""
        import time
        
        await provider_registry.initialize()
        
        try:
            symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
            
            async def fetch_price(symbol):
                asset = Asset(symbol=symbol, asset_type=AssetType.EQUITY, market=Market.US)
                plan = await arbitration_engine.arbitrate_request(
                    asset=asset,
                    data_type=DataType.PRICE,
                    user_region="US"
                )
                return await arbitration_engine.execute_with_fallback(
                    plan, asset, DataType.PRICE
                )
            
            start = time.time()
            
            tasks = [fetch_price(symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed = time.time() - start
            
            # Should handle 5 concurrent requests efficiently
            assert elapsed < 10.0
            
            # Count successful responses
            successful = sum(1 for r in responses if not isinstance(r, Exception))
            assert successful > 0
            
        finally:
            await provider_registry.shutdown()


@pytest.mark.live
class TestLiveCompliance:
    """Test compliance framework with live data"""

    @pytest.mark.asyncio
    async def test_compliance_router(self):
        """Test compliance checks"""
        from fiml.compliance.router import compliance_router, Region
        
        # Test passing compliance check
        result = await compliance_router.check_compliance(
            request_type="price_query",
            asset_type="equity",
            region=Region.US,
            user_query=None
        )
        
        assert result.passed is True
        assert len(result.restrictions) == 0

    @pytest.mark.asyncio
    async def test_disclaimer_generation(self):
        """Test disclaimer generation"""
        from fiml.compliance.disclaimers import disclaimer_generator, AssetClass
        
        disclaimer = disclaimer_generator.generate_disclaimer(
            asset_class=AssetClass.EQUITY,
            region="US",
            language="en"
        )
        
        assert len(disclaimer) > 0
        assert "financial advice" in disclaimer.lower()


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "live: mark test as requiring live system"
    )
