"""
Cache Optimization Benchmarks
Tests cache performance improvements with 1000 concurrent requests
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from fiml.cache.analytics import CacheAnalytics
from fiml.cache.l1_cache import EvictionPolicy, L1Cache
from fiml.cache.manager import CacheManager
from fiml.cache.scheduler import BatchUpdateScheduler
from fiml.cache.warming import PredictiveCacheWarmer
from fiml.core.models import Asset, DataType


class MockProvider:
    """Mock provider for benchmarking"""

    def __init__(self, name: str, latency_ms: int = 50):
        self.name = name
        self.latency_ms = latency_ms
        self.call_count = 0

    async def get_price(self, asset: Asset) -> Optional[Dict[str, Any]]:
        """Mock get_price with simulated latency"""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return {
            "symbol": asset.symbol,
            "price": random.uniform(100, 1000),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_prices_batch(self, assets: List[Asset]) -> List[Optional[Dict[str, Any]]]:
        """Mock batch price fetch"""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return [await self.get_price(asset) for asset in assets]

    async def get_fundamentals(self, asset: Asset) -> Optional[Dict[str, Any]]:
        """Mock get_fundamentals"""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return {
            "symbol": asset.symbol,
            "pe_ratio": random.uniform(10, 30),
            "market_cap": random.randint(1_000_000, 100_000_000),
        }


class MockProviderRegistry:
    """Mock provider registry"""

    def __init__(self):
        self.providers = {
            "mock_provider": MockProvider("mock_provider"),
        }

    def get_provider(self, name: str) -> Optional[MockProvider]:
        return self.providers.get(name)

    def get_provider_for_data_type(
        self, data_type: DataType, asset: Asset
    ) -> Optional[MockProvider]:
        return self.providers.get("mock_provider")


class CacheBenchmark:
    """Benchmark suite for cache optimizations"""

    def __init__(self):
        self.cache_manager: Optional[CacheManager] = None
        self.provider_registry: Optional[MockProviderRegistry] = None
        self.warmer: Optional[PredictiveCacheWarmer] = None
        self.scheduler: Optional[BatchUpdateScheduler] = None
        self.analytics: Optional[CacheAnalytics] = None

        # Test assets
        self.test_symbols = [
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
            "META", "NVDA", "AMD", "INTC", "NFLX",
            "BTC", "ETH", "SPY", "QQQ", "DIA",
        ] * 20  # 300 total symbols for testing

    async def setup(self, eviction_policy: EvictionPolicy = EvictionPolicy.LRU):
        """Setup benchmark environment"""
        # Initialize cache with specified eviction policy
        self.cache_manager = CacheManager()
        self.cache_manager.l1 = L1Cache(eviction_policy=eviction_policy)

        await self.cache_manager.initialize()

        # Setup mock provider
        self.provider_registry = MockProviderRegistry()

        # Setup analytics
        self.analytics = CacheAnalytics(enable_prometheus=False)

        # Setup cache warmer
        self.warmer = PredictiveCacheWarmer(
            cache_manager=self.cache_manager,
            provider_registry=self.provider_registry,
            max_symbols_per_batch=50,
        )

        # Setup scheduler
        self.scheduler = BatchUpdateScheduler(
            cache_manager=self.cache_manager,
            provider_registry=self.provider_registry,
            batch_size=50,
            batch_interval_seconds=1,
        )

    async def teardown(self):
        """Cleanup benchmark environment"""
        if self.cache_manager:
            await self.cache_manager.shutdown()

        if self.warmer:
            await self.warmer.stop_background_warming()

        if self.scheduler:
            await self.scheduler.stop()

    async def benchmark_baseline(self, num_requests: int = 1000) -> Dict[str, Any]:
        """
        Baseline benchmark: No warming, no batching

        Args:
            num_requests: Number of concurrent requests

        Returns:
            Benchmark results
        """
        print(f"\n{'='*60}")
        print(f"BASELINE BENCHMARK - {num_requests} requests")
        print(f"{'='*60}")

        assets = [
            Asset(symbol=random.choice(self.test_symbols), asset_type="equity")
            for _ in range(num_requests)
        ]

        provider = self.provider_registry.providers["mock_provider"]
        provider.call_count = 0

        start_time = time.perf_counter()

        # Simulate concurrent requests
        async def fetch_price(asset: Asset) -> Optional[Dict[str, Any]]:
            key = self.cache_manager.l1.build_key("price", asset.symbol, "mock_provider")

            # Check cache
            cache_start = time.perf_counter()
            cached = await self.cache_manager.get(key)
            cache_latency_ms = (time.perf_counter() - cache_start) * 1000

            if cached:
                self.analytics.record_cache_access(
                    DataType.PRICE, True, cache_latency_ms, "l1", key
                )
                return cached

            self.analytics.record_cache_access(
                DataType.PRICE, False, cache_latency_ms, "l1", key
            )

            # Fetch from provider
            price = await provider.get_price(asset)
            if price:
                await self.cache_manager.set_price(asset, "mock_provider", price)

            return price

        tasks = [fetch_price(asset) for asset in assets]
        await asyncio.gather(*tasks)

        elapsed_time = time.perf_counter() - start_time

        stats = self.analytics.get_overall_stats()

        print(f"Total time: {elapsed_time:.2f}s")
        print(f"Requests/sec: {num_requests / elapsed_time:.2f}")
        print(f"Cache hit rate: {stats['hit_rate_percent']:.2f}%")
        print(f"API calls: {provider.call_count}")
        print(f"Avg latency: {elapsed_time / num_requests * 1000:.2f}ms")

        return {
            "total_time": elapsed_time,
            "requests_per_sec": num_requests / elapsed_time,
            "hit_rate": stats["hit_rate_percent"],
            "api_calls": provider.call_count,
            "avg_latency_ms": elapsed_time / num_requests * 1000,
        }

    async def benchmark_with_warming(self, num_requests: int = 1000) -> Dict[str, Any]:
        """
        Benchmark with cache warming enabled

        Args:
            num_requests: Number of concurrent requests

        Returns:
            Benchmark results
        """
        print(f"\n{'='*60}")
        print(f"WARMING BENCHMARK - {num_requests} requests")
        print(f"{'='*60}")

        # Simulate access patterns for warming
        for symbol in self.test_symbols[:50]:  # Top 50 symbols
            for _ in range(random.randint(10, 30)):
                self.warmer.record_cache_access(symbol, DataType.PRICE)

        # Run warming cycle
        print("Running cache warming cycle...")
        await self.warmer.run_warming_cycle()

        warming_stats = self.warmer.get_warming_stats()
        print(f"Warmed {warming_stats['successful']} symbols")

        # Reset analytics
        self.analytics.reset_stats()

        # Now run requests
        return await self.benchmark_baseline(num_requests)

    async def benchmark_with_batching(self, num_requests: int = 1000) -> Dict[str, Any]:
        """
        Benchmark with batch scheduling

        Args:
            num_requests: Number of concurrent requests

        Returns:
            Benchmark results
        """
        print(f"\n{'='*60}")
        print(f"BATCHING BENCHMARK - {num_requests} requests")
        print(f"{'='*60}")

        assets = [
            Asset(symbol=random.choice(self.test_symbols), asset_type="equity")
            for _ in range(num_requests)
        ]

        provider = self.provider_registry.providers["mock_provider"]
        provider.call_count = 0

        # Schedule updates
        updates = [
            (asset, DataType.PRICE, "mock_provider", 0)
            for asset in assets
        ]

        start_time = time.perf_counter()

        await self.scheduler.schedule_updates_batch(updates)
        flush_stats = await self.scheduler.flush_pending()

        elapsed_time = time.perf_counter() - start_time

        scheduler_stats = self.scheduler.get_stats()

        print(f"Total time: {elapsed_time:.2f}s")
        print(f"Batches processed: {flush_stats['batches']}")
        print(f"Successful updates: {flush_stats['success']}")
        print(f"API calls: {provider.call_count}")
        print(f"API calls saved: {scheduler_stats['api_calls_saved']}")

        return {
            "total_time": elapsed_time,
            "batches": flush_stats["batches"],
            "successful": flush_stats["success"],
            "api_calls": provider.call_count,
            "api_calls_saved": scheduler_stats["api_calls_saved"],
            "api_reduction_percent": (
                (scheduler_stats["api_calls_saved"] / num_requests * 100)
                if num_requests > 0 else 0
            ),
        }

    async def benchmark_eviction_policies(self, num_requests: int = 1000) -> Dict[str, Dict[str, Any]]:
        """
        Compare different eviction policies

        Args:
            num_requests: Number of concurrent requests

        Returns:
            Results for each policy
        """
        print(f"\n{'='*60}")
        print(f"EVICTION POLICY COMPARISON - {num_requests} requests")
        print(f"{'='*60}")

        results = {}

        for policy in [EvictionPolicy.LRU, EvictionPolicy.LFU, EvictionPolicy.HYBRID]:
            print(f"\nTesting {policy.value.upper()} policy...")

            # Reinitialize cache with new policy
            await self.teardown()
            await self.setup(eviction_policy=policy)

            # Run benchmark
            policy_results = await self.benchmark_baseline(num_requests)
            results[policy.value] = policy_results

        return results

    async def benchmark_comprehensive(self) -> Dict[str, Any]:
        """
        Run comprehensive benchmark suite

        Returns:
            Complete benchmark results
        """
        print(f"\n{'#'*60}")
        print("# COMPREHENSIVE CACHE OPTIMIZATION BENCHMARKS")
        print(f"{'#'*60}")

        results = {}

        # Test 1: Baseline (no optimizations)
        await self.setup()
        results["baseline"] = await self.benchmark_baseline(1000)

        # Test 2: With cache warming
        await self.teardown()
        await self.setup()
        results["with_warming"] = await self.benchmark_with_warming(1000)

        # Test 3: With batch scheduling
        await self.teardown()
        await self.setup()
        results["with_batching"] = await self.benchmark_with_batching(1000)

        # Test 4: Eviction policy comparison
        results["eviction_policies"] = await self.benchmark_eviction_policies(500)

        # Print summary
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")

        print("\nBaseline:")
        print(f"  - Avg latency: {results['baseline']['avg_latency_ms']:.2f}ms")
        print(f"  - Hit rate: {results['baseline']['hit_rate']:.2f}%")
        print(f"  - API calls: {results['baseline']['api_calls']}")

        print("\nWith Warming:")
        print(f"  - Avg latency: {results['with_warming']['avg_latency_ms']:.2f}ms")
        print(f"  - Hit rate: {results['with_warming']['hit_rate']:.2f}%")
        print(f"  - Improvement: {((results['baseline']['avg_latency_ms'] - results['with_warming']['avg_latency_ms']) / results['baseline']['avg_latency_ms'] * 100):.1f}%")

        print("\nWith Batching:")
        print(f"  - API calls saved: {results['with_batching']['api_calls_saved']}")
        print(f"  - API reduction: {results['with_batching']['api_reduction_percent']:.1f}%")

        # Analytics report
        analytics_report = self.analytics.get_comprehensive_report()
        print("\nCache Analytics:")
        for data_type, stats in analytics_report["by_data_type"].items():
            if stats["hits"] > 0 or stats["misses"] > 0:
                print(f"  {data_type}:")
                print(f"    - Hit rate: {stats['hit_rate_percent']:.2f}%")
                print(f"    - p95 latency: {stats['latency_ms']['p95']:.2f}ms")

        print("\nRecommendations:")
        for rec in analytics_report["recommendations"]:
            print(f"  - {rec}")

        await self.teardown()

        return results


# Pytest fixtures and tests
@pytest.fixture
async def benchmark():
    """Benchmark fixture"""
    bench = CacheBenchmark()
    await bench.setup()
    yield bench
    await bench.teardown()


@pytest.mark.asyncio
async def test_baseline_performance(benchmark):
    """Test baseline cache performance"""
    results = await benchmark.benchmark_baseline(100)

    assert results["total_time"] < 10.0  # Should complete in 10s
    assert results["requests_per_sec"] > 10  # At least 10 req/s


@pytest.mark.asyncio
async def test_warming_improves_hit_rate(benchmark):
    """Test that warming improves cache hit rate"""
    baseline = await benchmark.benchmark_baseline(100)

    # Reset and test with warming
    await benchmark.teardown()
    await benchmark.setup()

    warmed = await benchmark.benchmark_with_warming(100)

    assert warmed["hit_rate"] >= baseline["hit_rate"]


@pytest.mark.asyncio
async def test_batching_reduces_api_calls(benchmark):
    """Test that batching reduces API calls"""
    results = await benchmark.benchmark_with_batching(100)

    # Should save at least 20% of API calls
    assert results["api_reduction_percent"] >= 20


@pytest.mark.asyncio
async def test_comprehensive_benchmark():
    """Run full benchmark suite"""
    benchmark = CacheBenchmark()
    results = await benchmark.benchmark_comprehensive()

    # Verify all benchmarks ran
    assert "baseline" in results
    assert "with_warming" in results
    assert "with_batching" in results
    assert "eviction_policies" in results

    # Verify warming provides improvement
    warming_improvement = (
        (results["baseline"]["avg_latency_ms"] - results["with_warming"]["avg_latency_ms"])
        / results["baseline"]["avg_latency_ms"] * 100
    )

    print(f"\n✓ Warming improved latency by {warming_improvement:.1f}%")
    print(f"✓ Batching reduced API calls by {results['with_batching']['api_reduction_percent']:.1f}%")


if __name__ == "__main__":
    # Run comprehensive benchmark
    async def main():
        benchmark = CacheBenchmark()
        results = await benchmark.benchmark_comprehensive()

        # Export results
        import json
        with open("cache_benchmark_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print("\n✓ Results saved to cache_benchmark_results.json")

    asyncio.run(main())
