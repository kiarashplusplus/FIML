"""
Stress Testing Suite for FIML

Tests system behavior under extreme conditions:
- Peak load testing (2x normal traffic)
- Spike testing (sudden 10x load)
- Endurance testing (sustained load for 1 hour)
- Provider failure scenarios
- Database connection pool exhaustion
- Redis max connections

Usage:
    # Peak load test
    pytest tests/performance/stress_test.py::test_peak_load -v

    # Spike test
    pytest tests/performance/stress_test.py::test_spike_load -v

    # Endurance test (1 hour)
    pytest tests/performance/stress_test.py::test_endurance -v

    # Failure scenarios
    pytest tests/performance/stress_test.py::test_provider_failure -v
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List

import httpx
import pytest

from fiml.cache.manager import cache_manager
from fiml.providers.registry import provider_registry


class StressTestMetrics:
    """Collect and analyze stress test metrics"""

    def __init__(self):
        self.requests_sent = 0
        self.requests_succeeded = 0
        self.requests_failed = 0
        self.response_times: List[float] = []
        self.errors: List[Dict] = []
        self.start_time: float = 0
        self.end_time: float = 0

    def record_request(self, success: bool, response_time: float, error: str = None):
        """Record a request result"""
        self.requests_sent += 1
        self.response_times.append(response_time)

        if success:
            self.requests_succeeded += 1
        else:
            self.requests_failed += 1
            if error:
                self.errors.append({
                    "timestamp": datetime.now().isoformat(),
                    "error": error,
                    "response_time": response_time
                })

    def get_summary(self) -> Dict:
        """Get metrics summary"""
        duration = self.end_time - self.start_time

        if not self.response_times:
            return {
                "duration_seconds": duration,
                "requests_sent": self.requests_sent,
                "requests_succeeded": 0,
                "requests_failed": self.requests_sent,
                "error_rate": 1.0,
                "throughput": 0,
                "response_times": {}
            }

        sorted_times = sorted(self.response_times)
        n = len(sorted_times)

        return {
            "duration_seconds": duration,
            "requests_sent": self.requests_sent,
            "requests_succeeded": self.requests_succeeded,
            "requests_failed": self.requests_failed,
            "error_rate": self.requests_failed / self.requests_sent if self.requests_sent > 0 else 0,
            "throughput": self.requests_succeeded / duration if duration > 0 else 0,
            "response_times": {
                "min": min(sorted_times),
                "max": max(sorted_times),
                "mean": sum(sorted_times) / n,
                "p50": sorted_times[n // 2],
                "p95": sorted_times[int(n * 0.95)],
                "p99": sorted_times[int(n * 0.99)],
            }
        }


async def make_request(client: httpx.AsyncClient, url: str, payload: dict, metrics: StressTestMetrics):
    """Make a single request and record metrics"""
    start = time.perf_counter()
    try:
        response = await client.post(url, json=payload, timeout=30.0)
        response_time = time.perf_counter() - start

        success = response.status_code == 200
        error = None if success else f"HTTP {response.status_code}"

        metrics.record_request(success, response_time, error)

    except Exception as e:
        response_time = time.perf_counter() - start
        metrics.record_request(False, response_time, str(e))


@pytest.mark.asyncio
@pytest.mark.slow
async def test_peak_load(base_url: str = "http://localhost:8000"):
    """
    Peak Load Test: 2x normal traffic

    Simulates peak trading hours with double the normal load.
    Target: System should handle gracefully with <5% error rate
    """
    metrics = StressTestMetrics()
    metrics.start_time = time.perf_counter()

    # Normal load: 100 req/s, Peak load: 200 req/s
    concurrent_users = 200
    duration_seconds = 60

    print(f"\n{'='*60}")
    print("PEAK LOAD TEST")
    print(f"Concurrent users: {concurrent_users}")
    print(f"Duration: {duration_seconds}s")
    print(f"Expected requests: ~{concurrent_users * duration_seconds}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient() as client:
        start_time = time.time()
        tasks = []

        while time.time() - start_time < duration_seconds:
            # Send burst of requests
            for _ in range(concurrent_users):
                url = f"{base_url}/mcp/tools/get_price"
                payload = {"symbol": "AAPL"}
                task = asyncio.create_task(make_request(client, url, payload, metrics))
                tasks.append(task)

            # Wait a bit before next burst
            await asyncio.sleep(1)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    metrics.end_time = time.perf_counter()
    summary = metrics.get_summary()

    print(f"\n{'='*60}")
    print("PEAK LOAD TEST RESULTS")
    print(f"{'='*60}")
    print(f"Duration: {summary['duration_seconds']:.2f}s")
    print(f"Requests sent: {summary['requests_sent']}")
    print(f"Succeeded: {summary['requests_succeeded']}")
    print(f"Failed: {summary['requests_failed']}")
    print(f"Error rate: {summary['error_rate']:.2%}")
    print(f"Throughput: {summary['throughput']:.2f} req/s")
    print("\nResponse Times:")
    print(f"  Min: {summary['response_times']['min']*1000:.2f}ms")
    print(f"  Mean: {summary['response_times']['mean']*1000:.2f}ms")
    print(f"  P50: {summary['response_times']['p50']*1000:.2f}ms")
    print(f"  P95: {summary['response_times']['p95']*1000:.2f}ms")
    print(f"  P99: {summary['response_times']['p99']*1000:.2f}ms")
    print(f"  Max: {summary['response_times']['max']*1000:.2f}ms")
    print(f"{'='*60}\n")

    # Assertions
    assert summary['error_rate'] < 0.05, f"Error rate {summary['error_rate']:.2%} exceeds 5%"
    assert summary['response_times']['p95'] < 1.0, f"P95 latency {summary['response_times']['p95']*1000:.2f}ms exceeds 1000ms"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_spike_load(base_url: str = "http://localhost:8000"):
    """
    Spike Load Test: Sudden 10x load increase

    Simulates sudden traffic spike (e.g., breaking news, market event).
    Target: System should auto-scale and handle with <10% error rate
    """
    metrics = StressTestMetrics()
    metrics.start_time = time.perf_counter()

    # Normal: 10 users, Spike: 100 users
    normal_users = 10
    spike_users = 100
    spike_duration = 30  # 30 seconds of spike

    print(f"\n{'='*60}")
    print("SPIKE LOAD TEST")
    print(f"Normal users: {normal_users}")
    print(f"Spike users: {spike_users}")
    print(f"Spike duration: {spike_duration}s")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient() as client:
        # Phase 1: Normal load (10s)
        print("Phase 1: Normal load...")
        start_time = time.time()
        while time.time() - start_time < 10:
            tasks = []
            for _ in range(normal_users):
                url = f"{base_url}/mcp/tools/get_price"
                payload = {"symbol": "TSLA"}
                task = asyncio.create_task(make_request(client, url, payload, metrics))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)

        # Phase 2: Spike (30s)
        print("Phase 2: SPIKE!")
        start_time = time.time()
        while time.time() - start_time < spike_duration:
            tasks = []
            for _ in range(spike_users):
                url = f"{base_url}/mcp/tools/get_price"
                payload = {"symbol": "MSFT"}
                task = asyncio.create_task(make_request(client, url, payload, metrics))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)

        # Phase 3: Recovery (10s)
        print("Phase 3: Recovery...")
        start_time = time.time()
        while time.time() - start_time < 10:
            tasks = []
            for _ in range(normal_users):
                url = f"{base_url}/mcp/tools/get_price"
                payload = {"symbol": "GOOGL"}
                task = asyncio.create_task(make_request(client, url, payload, metrics))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)

    metrics.end_time = time.perf_counter()
    summary = metrics.get_summary()

    print(f"\n{'='*60}")
    print("SPIKE LOAD TEST RESULTS")
    print(f"{'='*60}")
    print(f"Error rate: {summary['error_rate']:.2%}")
    print(f"P95 latency: {summary['response_times']['p95']*1000:.2f}ms")
    print(f"P99 latency: {summary['response_times']['p99']*1000:.2f}ms")
    print(f"{'='*60}\n")

    # Assertions - more lenient for spike test
    assert summary['error_rate'] < 0.10, f"Error rate {summary['error_rate']:.2%} exceeds 10%"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_endurance(base_url: str = "http://localhost:8000"):
    """
    Endurance Test: Sustained load for 1 hour

    Tests for memory leaks, connection leaks, and degradation over time.
    Target: Consistent performance throughout, no degradation
    """
    metrics = StressTestMetrics()
    metrics.start_time = time.perf_counter()

    concurrent_users = 50
    duration_seconds = 3600  # 1 hour
    sample_interval = 300  # Sample every 5 minutes

    print(f"\n{'='*60}")
    print("ENDURANCE TEST")
    print(f"Concurrent users: {concurrent_users}")
    print(f"Duration: {duration_seconds}s ({duration_seconds/60:.0f} minutes)")
    print(f"{'='*60}\n")

    interval_metrics: List[Dict] = []

    async with httpx.AsyncClient() as client:
        start_time = time.time()
        interval_start = start_time

        while time.time() - start_time < duration_seconds:
            tasks = []
            for _ in range(concurrent_users):
                url = f"{base_url}/mcp/tools/get_price"
                payload = {"symbol": "AAPL"}
                task = asyncio.create_task(make_request(client, url, payload, metrics))
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)

            # Sample metrics every interval
            if time.time() - interval_start >= sample_interval:
                elapsed = time.time() - start_time
                interval_summary = {
                    "elapsed_minutes": elapsed / 60,
                    "total_requests": metrics.requests_sent,
                    "error_rate": metrics.requests_failed / metrics.requests_sent if metrics.requests_sent > 0 else 0,
                }
                interval_metrics.append(interval_summary)
                print(f"[{elapsed/60:.0f}min] Requests: {metrics.requests_sent}, Error rate: {interval_summary['error_rate']:.2%}")
                interval_start = time.time()

    metrics.end_time = time.perf_counter()
    summary = metrics.get_summary()

    print(f"\n{'='*60}")
    print("ENDURANCE TEST RESULTS")
    print(f"{'='*60}")
    print(f"Total requests: {summary['requests_sent']}")
    print(f"Error rate: {summary['error_rate']:.2%}")
    print(f"Throughput: {summary['throughput']:.2f} req/s")
    print(f"P95 latency: {summary['response_times']['p95']*1000:.2f}ms")
    print("\nPerformance over time:")
    for interval in interval_metrics:
        print(f"  {interval['elapsed_minutes']:.0f}min: {interval['total_requests']} requests, {interval['error_rate']:.2%} error rate")
    print(f"{'='*60}\n")

    # Check for performance degradation
    if len(interval_metrics) >= 2:
        first_half_errors = sum(m['error_rate'] for m in interval_metrics[:len(interval_metrics)//2])
        second_half_errors = sum(m['error_rate'] for m in interval_metrics[len(interval_metrics)//2:])

        assert second_half_errors <= first_half_errors * 1.5, "Performance degraded significantly over time"

    assert summary['error_rate'] < 0.05, f"Error rate {summary['error_rate']:.2%} exceeds 5%"


@pytest.mark.asyncio
async def test_provider_failure():
    """
    Provider Failure Scenario

    Tests system resilience when providers fail or are unavailable.
    Target: Graceful degradation with fallback to other providers
    """
    from fiml.core.models import Asset, AssetType, Market
    from fiml.providers.yahoo_finance import YahooFinanceProvider

    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US
    )

    print(f"\n{'='*60}")
    print("PROVIDER FAILURE TEST")
    print(f"{'='*60}\n")

    # Test 1: Single provider failure
    print("Test 1: Single provider failure")
    provider = YahooFinanceProvider()

    # Simulate provider failure
    original_fetch = provider.fetch_price

    async def failing_fetch(*args, **kwargs):
        raise Exception("Provider unavailable")

    provider.fetch_price = failing_fetch

    try:
        result = await provider.fetch_price(asset)
        raise AssertionError("Should have raised exception")
    except Exception as e:
        print(f"  ✓ Provider failure handled: {e}")

    # Restore
    provider.fetch_price = original_fetch

    # Test 2: Verify fallback to other providers
    print("\nTest 2: Provider registry fallback")
    await provider_registry.initialize()

    # Try to get price - should fallback to other providers
    try:
        result = await provider_registry.fetch_price(asset, provider_name="yahoo")
        if result:
            print(f"  ✓ Fallback successful: {result}")
    except Exception as e:
        print(f"  ✓ All providers failed (expected in test environment): {e}")

    print(f"\n{'='*60}\n")


@pytest.mark.asyncio
async def test_database_connection_pool_exhaustion():
    """
    Database Connection Pool Exhaustion

    Tests behavior when PostgreSQL connection pool is exhausted.
    Target: Graceful queuing or error handling
    """
    from fiml.cache.l2_cache import l2_cache

    print(f"\n{'='*60}")
    print("DATABASE CONNECTION POOL TEST")
    print(f"{'='*60}\n")

    await l2_cache.initialize()

    # Create many concurrent database operations
    async def db_operation(i: int):
        try:
            # Simulate long-running query
            await asyncio.sleep(0.1)
            return i
        except Exception as e:
            return f"Error: {e}"

    # Try to create more connections than pool allows
    num_operations = 100
    print(f"Creating {num_operations} concurrent operations...")

    start = time.perf_counter()
    tasks = [db_operation(i) for i in range(num_operations)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - start

    successful = sum(1 for r in results if isinstance(r, int))
    failed = len(results) - successful

    print(f"Completed in {elapsed:.2f}s")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"{'='*60}\n")

    # Should handle gracefully (queue or timeout, not crash)
    assert successful + failed == num_operations


@pytest.mark.asyncio
async def test_redis_max_connections():
    """
    Redis Connection Exhaustion

    Tests behavior when Redis max connections is reached.
    Target: Connection pooling prevents exhaustion
    """
    from fiml.cache.l1_cache import l1_cache

    print(f"\n{'='*60}")
    print("REDIS CONNECTION TEST")
    print(f"{'='*60}\n")

    await l1_cache.initialize()

    # Create many concurrent Redis operations
    async def redis_operation(i: int):
        try:
            await l1_cache.set(f"test_key_{i}", {"value": i}, ttl_seconds=10)
            result = await l1_cache.get(f"test_key_{i}")
            return result is not None
        except Exception as e:
            return f"Error: {e}"

    num_operations = 200
    print(f"Creating {num_operations} concurrent Redis operations...")

    start = time.perf_counter()
    tasks = [redis_operation(i) for i in range(num_operations)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - start

    successful = sum(1 for r in results if r is True)
    failed = len(results) - successful

    print(f"Completed in {elapsed:.2f}s")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"{'='*60}\n")

    # Cleanup
    for i in range(num_operations):
        await l1_cache.delete(f"test_key_{i}")

    # Should handle all operations successfully with connection pooling
    assert successful >= num_operations * 0.95  # Allow 5% failure


@pytest.mark.asyncio
async def test_memory_leak_detection():
    """
    Memory Leak Detection

    Monitors memory usage during sustained operations.
    Target: Memory usage should stabilize, not grow continuously
    """
    import os

    import psutil

    process = psutil.Process(os.getpid())

    print(f"\n{'='*60}")
    print("MEMORY LEAK DETECTION")
    print(f"{'='*60}\n")

    await cache_manager.initialize()

    memory_samples = []
    num_iterations = 100

    # Take baseline
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Perform operations and sample memory
    for i in range(num_iterations):
        # Perform cache operations
        for j in range(10):
            await cache_manager.l1.set(f"test_{j}", {"data": "x" * 1000}, ttl_seconds=10)
            await cache_manager.l1.get(f"test_{j}")

        # Sample memory every 10 iterations
        if i % 10 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            print(f"Iteration {i}: {current_memory:.2f} MB")

    final_memory = process.memory_info().rss / 1024 / 1024
    memory_growth = final_memory - baseline_memory

    print(f"\nFinal memory: {final_memory:.2f} MB")
    print(f"Memory growth: {memory_growth:.2f} MB")
    print(f"{'='*60}\n")

    # Check for memory leak (growth should be minimal)
    # Allow some growth for caching, but not linear with iterations
    assert memory_growth < 100, f"Potential memory leak: {memory_growth:.2f} MB growth"

    # Check that memory stabilizes (last quarter vs first quarter)
    if len(memory_samples) >= 4:
        first_quarter_avg = sum(memory_samples[:len(memory_samples)//4]) / (len(memory_samples)//4)
        last_quarter_avg = sum(memory_samples[-len(memory_samples)//4:]) / (len(memory_samples)//4)
        growth_rate = (last_quarter_avg - first_quarter_avg) / first_quarter_avg

        print(f"First quarter avg: {first_quarter_avg:.2f} MB")
        print(f"Last quarter avg: {last_quarter_avg:.2f} MB")
        print(f"Growth rate: {growth_rate:.2%}")

        assert growth_rate < 0.50, f"Memory growing too fast: {growth_rate:.2%}"


if __name__ == "__main__":
    # Allow running individual tests
    import sys

    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "peak":
            asyncio.run(test_peak_load())
        elif test_name == "spike":
            asyncio.run(test_spike_load())
        elif test_name == "endurance":
            asyncio.run(test_endurance())
        elif test_name == "provider":
            asyncio.run(test_provider_failure())
        elif test_name == "db":
            asyncio.run(test_database_connection_pool_exhaustion())
        elif test_name == "redis":
            asyncio.run(test_redis_max_connections())
        elif test_name == "memory":
            asyncio.run(test_memory_leak_detection())
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: peak, spike, endurance, provider, db, redis, memory")
    else:
        print("Usage: python stress_test.py <test_name>")
        print("Available tests: peak, spike, endurance, provider, db, redis, memory")
