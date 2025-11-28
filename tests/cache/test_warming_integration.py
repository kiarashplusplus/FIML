
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fiml.cache.warming import PredictiveCacheWarmer
from fiml.core.models import Asset, DataType, AssetType

@pytest.mark.asyncio
async def test_cache_warmer_initialization():
    warmer = PredictiveCacheWarmer(None, None)
    
    mock_cache_manager = AsyncMock()
    mock_provider_registry = AsyncMock()
    
    with patch("fiml.cache.manager.cache_manager", mock_cache_manager), \
         patch("fiml.providers.provider_registry", mock_provider_registry):
        
        await warmer.initialize()
        
        assert warmer.cache_manager == mock_cache_manager
        assert warmer.provider_registry == mock_provider_registry

@pytest.mark.asyncio
async def test_warm_cache_batch():
    warmer = PredictiveCacheWarmer(None, None)
    warmer.cache_manager = AsyncMock()
    # provider_registry should be MagicMock because get_provider_for_data_type is sync
    warmer.provider_registry = MagicMock()
    
    # Mock provider response
    mock_provider = AsyncMock()
    mock_provider.name = "mock_provider"
    mock_provider.get_price.return_value = {"price": 150.0}
    mock_provider.get_fundamentals.return_value = {"pe": 30.0}
    
    # Configure the sync method to return the mock provider
    warmer.provider_registry.get_provider_for_data_type.return_value = mock_provider
    
    symbols = ["AAPL", "MSFT"]
    results = await warmer.warm_cache_batch(symbols, concurrency=2)
    
    assert len(results) == 2
    assert results["AAPL"] is True
    assert results["MSFT"] is True
    
    # Verify calls
    assert warmer.provider_registry.get_provider_for_data_type.call_count >= 4 # 2 symbols * 2 data types
    assert warmer.cache_manager.set_price.call_count == 2
    assert warmer.cache_manager.set_fundamentals.call_count == 2

@pytest.mark.asyncio
async def test_warm_cache_batch_failure():
    warmer = PredictiveCacheWarmer(None, None)
    warmer.cache_manager = AsyncMock()
    warmer.provider_registry = MagicMock()
    
    # Mock provider failure
    warmer.provider_registry.get_provider_for_data_type.side_effect = Exception("Provider error")
    
    symbols = ["FAIL"]
    results = await warmer.warm_cache_batch(symbols)
    
    assert results["FAIL"] is False
