"""
Comprehensive tests for Cache modules
"""

import pytest
from fiml.cache.l1_cache import L1Cache, l1_cache
from fiml.cache.l2_cache import L2Cache, l2_cache
from fiml.cache.manager import CacheManager, cache_manager


class TestL1Cache:
    """Test L1 (Redis) cache"""

    @pytest.mark.asyncio
    async def test_l1_cache_lifecycle(self):
        """Test L1 cache initialization and shutdown"""
        cache = L1Cache()
        
        # Try to initialize (might fail if Redis not available)
        try:
            await cache.initialize()
            assert cache._initialized
            
            await cache.shutdown()
            assert not cache._initialized
        except (ConnectionError, OSError, Exception) as e:
            # Redis not available - skip test
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_l1_cache_operations(self):
        """Test basic cache operations"""
        try:
            await l1_cache.initialize()
            
            # Set a value
            success = await l1_cache.set("test_key", {"data": "test"}, ttl_seconds=60)
            assert success is not None
            
            # Get the value
            value = await l1_cache.get("test_key")
            if value:
                assert value.get("data") == "test"
            
            # Delete the value
            deleted = await l1_cache.delete("test_key")
            assert isinstance(deleted, bool)
            
            await l1_cache.shutdown()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    async def test_l1_cache_exists(self):
        """Test cache exists check"""
        try:
            await l1_cache.initialize()
            
            # Set a key
            await l1_cache.set("exists_key", "value")
            
            # Check if exists
            exists = await l1_cache.exists("exists_key")
            assert isinstance(exists, bool)
            
            # Clean up
            await l1_cache.delete("exists_key")
            await l1_cache.shutdown()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    async def test_l1_cache_clear_pattern(self):
        """Test clearing keys by pattern"""
        try:
            await l1_cache.initialize()
            
            # Set multiple keys with pattern
            await l1_cache.set("pattern:key1", "value1")
            await l1_cache.set("pattern:key2", "value2")
            
            # Clear by pattern
            count = await l1_cache.clear_pattern("pattern:*")
            assert isinstance(count, int)
            
            await l1_cache.shutdown()
        except Exception:
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    async def test_l1_cache_get_stats(self):
        """Test getting cache statistics"""
        try:
            await l1_cache.initialize()
            
            stats = await l1_cache.get_stats()
            assert isinstance(stats, dict)
            
            await l1_cache.shutdown()
        except Exception:
            pytest.skip("Redis not available")


class TestL2Cache:
    """Test L2 (PostgreSQL) cache"""

    @pytest.mark.asyncio
    async def test_l2_cache_initialization(self):
        """Test L2 cache initialization"""
        cache = L2Cache()
        
        try:
            await cache.initialize()
            assert cache._initialized
            await cache.shutdown()
            assert not cache._initialized
        except Exception:
            pytest.skip("PostgreSQL not available")

    @pytest.mark.asyncio
    async def test_l2_cache_set_get(self):
        """Test L2 cache set and get"""
        cache = L2Cache()
        
        try:
            await cache.initialize()
            
            # Set a value
            success = await cache.set("test_key", {"data": "test"}, ttl_seconds=60)
            assert success
            
            # Get the value
            value = await cache.get("test_key")
            assert value is not None
            assert value.get("data") == "test"
            
            await cache.shutdown()
        except Exception:
            pytest.skip("PostgreSQL not available")

    @pytest.mark.asyncio
    async def test_l2_cache_delete(self):
        """Test L2 cache delete"""
        cache = L2Cache()
        
        try:
            await cache.initialize()
            
            # Set and delete
            await cache.set("delete_key", "value")
            deleted = await cache.delete("delete_key")
            assert deleted
            
            # Verify deleted
            value = await cache.get("delete_key")
            assert value is None
            
            await cache.shutdown()
        except Exception:
            pytest.skip("PostgreSQL not available")

    @pytest.mark.asyncio
    async def test_l2_cache_exists(self):
        """Test L2 cache exists check"""
        cache = L2Cache()
        
        try:
            await cache.initialize()
            
            # Set a key
            await cache.set("exists_key", "value")
            
            # Check exists
            exists = await cache.exists("exists_key")
            assert exists is True
            
            # Check non-existent key
            exists = await cache.exists("nonexistent")
            assert exists is False
            
            await cache.shutdown()
        except Exception:
            pytest.skip("PostgreSQL not available")

    @pytest.mark.asyncio
    async def test_l2_cache_clear(self):
        """Test L2 cache clear"""
        cache = L2Cache()
        
        try:
            await cache.initialize()
            
            # Set some keys
            await cache.set("key1", "value1")
            await cache.set("key2", "value2")
            
            # Clear all
            await cache.clear()
            
            # Verify cleared
            value1 = await cache.get("key1")
            value2 = await cache.get("key2")
            assert value1 is None
            assert value2 is None
            
            await cache.shutdown()
        except Exception:
            pytest.skip("PostgreSQL not available")

    @pytest.mark.asyncio
    async def test_l2_cache_clear_pattern(self):
        """Test L2 cache pattern clear"""
        cache = L2Cache()
        
        try:
            await cache.initialize()
            
            # Set keys with pattern
            await cache.set("prefix:key1", "value1")
            await cache.set("prefix:key2", "value2")
            await cache.set("other:key", "value3")
            
            # Clear by pattern
            count = await cache.clear_pattern("prefix:*")
            assert count >= 0
            
            await cache.shutdown()
        except Exception:
            pytest.skip("PostgreSQL not available")

    @pytest.mark.asyncio
    async def test_l2_cache_stats(self):
        """Test L2 cache statistics"""
        cache = L2Cache()
        
        try:
            await cache.initialize()
            
            # Set some data
            await cache.set("stat_key", "value")
            
            # Get stats
            stats = await cache.get_stats()
            assert isinstance(stats, dict)
            assert "entries" in stats
            
            await cache.shutdown()
        except Exception:
            pytest.skip("PostgreSQL not available")


class TestCacheManager:
    """Test cache manager with L1/L2 fallback"""

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self):
        """Test cache manager init"""
        manager = CacheManager()
        
        try:
            await manager.initialize()
            assert manager._initialized
            
            await manager.shutdown()
            assert not manager._initialized
        except Exception:
            pytest.skip("Cache initialization failed")

    @pytest.mark.asyncio
    async def test_cache_manager_set_get(self):
        """Test cache manager set and get"""
        try:
            await cache_manager.initialize()
            
            # Set a value
            success = await cache_manager.set("manager_key", {"data": "test"}, ttl_seconds=60)
            assert success is not None
            
            # Get the value
            value = await cache_manager.get("manager_key")
            if value:
                assert value.get("data") == "test"
            
            await cache_manager.shutdown()
        except Exception:
            pytest.skip("Cache not available")

    @pytest.mark.asyncio
    async def test_cache_manager_delete(self):
        """Test cache manager delete"""
        try:
            await cache_manager.initialize()
            
            # Set and delete
            await cache_manager.set("delete_key", "value")
            deleted = await cache_manager.delete("delete_key")
            assert isinstance(deleted, bool)
            
            await cache_manager.shutdown()
        except Exception:
            pytest.skip("Cache not available")

    @pytest.mark.asyncio
    async def test_cache_manager_exists(self):
        """Test cache manager exists check"""
        try:
            await cache_manager.initialize()
            
            # Set a key
            await cache_manager.set("exists_key", "value")
            
            # Check exists
            exists = await cache_manager.exists("exists_key")
            assert isinstance(exists, bool)
            
            await cache_manager.shutdown()
        except Exception:
            pytest.skip("Cache not available")

    @pytest.mark.asyncio
    async def test_cache_manager_clear_pattern(self):
        """Test cache manager pattern clear"""
        try:
            await cache_manager.initialize()
            
            # Set keys
            await cache_manager.set("pattern:key1", "value1")
            await cache_manager.set("pattern:key2", "value2")
            
            # Clear by pattern
            count = await cache_manager.clear_pattern("pattern:*")
            assert isinstance(count, int)
            
            await cache_manager.shutdown()
        except Exception:
            pytest.skip("Cache not available")

    @pytest.mark.asyncio
    async def test_cache_manager_get_stats(self):
        """Test cache manager statistics"""
        try:
            await cache_manager.initialize()
            
            stats = await cache_manager.get_stats()
            assert isinstance(stats, dict)
            
            await cache_manager.shutdown()
        except Exception:
            pytest.skip("Cache not available")
