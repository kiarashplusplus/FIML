"""
Performance benchmarks for Cache Layer (L1 and L2)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fiml.cache.manager import CacheManager
from fiml.cache.l1_cache import L1Cache
from fiml.cache.l2_cache import L2Cache


class TestCacheBenchmarks:
    """Benchmarks for cache operations"""

    @pytest.mark.asyncio
    async def test_l1_cache_write(self, benchmark, benchmark_asset):
        """Benchmark L1 (Redis) cache write performance"""
        cache = L1Cache()
        
        # Mock Redis connection to avoid actual Redis dependency
        with patch.object(cache, '_redis', AsyncMock()) as mock_redis:
            mock_redis.setex = AsyncMock()
            
            async def write_to_cache():
                data = {
                    "price": 150.50,
                    "volume": 1000000,
                    "timestamp": datetime.now().isoformat(),
                }
                await cache.set_price(benchmark_asset, data, ttl_seconds=60)
            
            await benchmark.pedantic(write_to_cache, rounds=10)

    @pytest.mark.asyncio
    async def test_l1_cache_read(self, benchmark, benchmark_asset):
        """Benchmark L1 (Redis) cache read performance"""
        cache = L1Cache()
        
        # Mock Redis with pre-populated data
        mock_data = '{"price": 150.50, "volume": 1000000}'
        with patch.object(cache, '_redis', AsyncMock()) as mock_redis:
            mock_redis.get = AsyncMock(return_value=mock_data)
            
            async def read_from_cache():
                return await cache.get_price(benchmark_asset)
            
            result = await benchmark.pedantic(read_from_cache, rounds=10)
            assert result is not None

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, benchmark, benchmark_asset):
        """Benchmark cache key generation"""
        cache = L1Cache()
        
        def generate_key():
            return cache._make_cache_key("price", benchmark_asset.symbol, benchmark_asset.market)
        
        result = benchmark(generate_key)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_cache_manager_get_with_fallback(self, benchmark, benchmark_asset):
        """Benchmark cache manager L1->L2 fallback logic"""
        manager = CacheManager()
        
        # Mock both cache layers
        with patch.object(manager.l1, 'get_price', AsyncMock(return_value=None)), \
             patch.object(manager.l2, 'get_price', AsyncMock(return_value={"price": 150.50})), \
             patch.object(manager.l1, 'set_price', AsyncMock()):
            
            async def get_with_fallback():
                return await manager.get_price(benchmark_asset)
            
            result = await benchmark.pedantic(get_with_fallback, rounds=10)
            assert result is not None

    @pytest.mark.asyncio
    async def test_batch_cache_operations(self, benchmark, benchmark_asset):
        """Benchmark batch cache operations"""
        cache = L1Cache()
        
        # Mock Redis pipeline for batch operations
        with patch.object(cache, '_redis', AsyncMock()) as mock_redis:
            mock_pipeline = AsyncMock()
            mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
            mock_pipeline.execute = AsyncMock(return_value=[None] * 10)
            
            async def batch_write():
                # Simulate writing 10 prices in a batch
                for i in range(10):
                    data = {"price": 150.0 + i, "volume": 1000000}
                    await cache.set_price(benchmark_asset, data, ttl_seconds=60)
            
            await benchmark.pedantic(batch_write, rounds=5)
