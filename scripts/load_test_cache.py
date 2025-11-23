"""
Cache Load Testing Script

Tests cache system under heavy load:
- 1000+ concurrent requests
- Latency measurement under load
- Hit rate tracking
- Memory pressure monitoring
"""

import asyncio
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from fiml.cache.l1_cache import l1_cache
from fiml.cache.utils import calculate_percentile


class CacheLoadTester:
    """Load testing for cache system"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    async def test_concurrent_reads(
        self,
        num_requests: int = 1000,
        num_unique_keys: int = 100
    ) -> Dict[str, Any]:
        """
        Test concurrent read performance

        Args:
            num_requests: Total number of concurrent requests
            num_unique_keys: Number of unique keys (affects hit rate)

        Returns:
            Test results with latency and hit rate metrics
        """
        print(f"\n{'='*60}")
        print(f"Testing {num_requests} concurrent reads ({num_unique_keys} unique keys)")
        print(f"{'='*60}")

        # Pre-populate cache with keys
        print(f"Pre-populating cache with {num_unique_keys} keys...")
        for i in range(num_unique_keys):
            await l1_cache.set(
                f"load_test_key_{i}",
                {
                    "id": i,
                    "data": f"value_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                ttl_seconds=300
            )

        # Prepare read tasks
        print(f"Executing {num_requests} concurrent reads...")
        tasks = []
        for i in range(num_requests):
            # Cycle through keys to create realistic access pattern
            key_id = i % num_unique_keys
            tasks.append(self._timed_get(f"load_test_key_{key_id}"))

        # Execute concurrently
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        # Analyze results
        latencies = [r["latency_ms"] for r in results]
        hits = sum(1 for r in results if r["hit"])

        return {
            "num_requests": num_requests,
            "num_unique_keys": num_unique_keys,
            "total_time_ms": total_time * 1000,
            "avg_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms": calculate_percentile(latencies, 95),
            "p99_latency_ms": calculate_percentile(latencies, 99),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "requests_per_second": num_requests / total_time,
            "hit_count": hits,
            "hit_rate_percent": (hits / num_requests) * 100,
        }

    async def test_concurrent_writes(
        self,
        num_requests: int = 1000
    ) -> Dict[str, Any]:
        """
        Test concurrent write performance

        Args:
            num_requests: Number of concurrent write operations

        Returns:
            Test results with write latency metrics
        """
        print(f"\n{'='*60}")
        print(f"Testing {num_requests} concurrent writes")
        print(f"{'='*60}")

        # Prepare write tasks
        tasks = []
        for i in range(num_requests):
            tasks.append(self._timed_set(
                f"write_test_key_{i}",
                {"id": i, "data": f"value_{i}"},
                ttl_seconds=60
            ))

        # Execute concurrently
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        # Analyze results
        latencies = [r["latency_ms"] for r in results]
        successes = sum(1 for r in results if r["success"])

        return {
            "num_requests": num_requests,
            "total_time_ms": total_time * 1000,
            "avg_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms": calculate_percentile(latencies, 95),
            "p99_latency_ms": calculate_percentile(latencies, 99),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "requests_per_second": num_requests / total_time,
            "success_count": successes,
            "success_rate_percent": (successes / num_requests) * 100,
        }

    async def test_mixed_workload(
        self,
        num_requests: int = 1000,
        read_ratio: float = 0.8  # 80% reads, 20% writes
    ) -> Dict[str, Any]:
        """
        Test mixed read/write workload

        Args:
            num_requests: Total number of requests
            read_ratio: Ratio of reads to total requests (0.0-1.0)

        Returns:
            Test results for mixed workload
        """
        print(f"\n{'='*60}")
        print(f"Testing {num_requests} mixed operations ({read_ratio*100:.0f}% reads)")
        print(f"{'='*60}")

        num_reads = int(num_requests * read_ratio)
        num_writes = num_requests - num_reads

        # Pre-populate some keys
        for i in range(100):
            await l1_cache.set(
                f"mixed_key_{i}",
                {"id": i, "data": f"value_{i}"},
                ttl_seconds=300
            )

        # Prepare mixed tasks
        tasks = []
        for i in range(num_reads):
            key_id = i % 100
            tasks.append(self._timed_get(f"mixed_key_{key_id}"))

        for i in range(num_writes):
            tasks.append(self._timed_set(
                f"mixed_key_{i % 100}",
                {"id": i, "data": f"updated_value_{i}"},
                ttl_seconds=300
            ))

        # Shuffle tasks for realistic pattern
        import random
        random.shuffle(tasks)

        # Execute concurrently
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        # Analyze results
        read_results = [r for r in results if "hit" in r]
        write_results = [r for r in results if "success" in r]

        read_latencies = [r["latency_ms"] for r in read_results]
        write_latencies = [r["latency_ms"] for r in write_results]

        return {
            "num_requests": num_requests,
            "num_reads": num_reads,
            "num_writes": num_writes,
            "total_time_ms": total_time * 1000,
            "requests_per_second": num_requests / total_time,
            "reads": {
                "avg_latency_ms": statistics.mean(read_latencies) if read_latencies else 0,
                "p95_latency_ms": calculate_percentile(read_latencies, 95),
                "hit_rate_percent": (sum(1 for r in read_results if r["hit"]) / num_reads * 100) if num_reads > 0 else 0,
            },
            "writes": {
                "avg_latency_ms": statistics.mean(write_latencies) if write_latencies else 0,
                "p95_latency_ms": calculate_percentile(write_latencies, 95),
                "success_rate_percent": (sum(1 for r in write_results if r["success"]) / num_writes * 100) if num_writes > 0 else 0,
            }
        }

    async def _timed_get(self, key: str) -> Dict[str, Any]:
        """Execute timed GET operation"""
        start = time.perf_counter()
        value = await l1_cache.get(key)
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "operation": "get",
            "key": key,
            "hit": value is not None,
            "latency_ms": latency_ms,
        }

    async def _timed_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int
    ) -> Dict[str, Any]:
        """Execute timed SET operation"""
        start = time.perf_counter()
        success = await l1_cache.set(key, value, ttl_seconds)
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "operation": "set",
            "key": key,
            "success": success,
            "latency_ms": latency_ms,
        }

    def print_results(self, results: Dict[str, Any]) -> None:
        """Pretty print test results"""
        print(f"\n{'='*60}")
        print("LOAD TEST RESULTS")
        print(f"{'='*60}")

        for key, value in results.items():
            if isinstance(value, dict):
                print(f"\n{key.upper()}:")
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, float):
                        print(f"  {subkey}: {subvalue:.2f}")
                    else:
                        print(f"  {subkey}: {subvalue}")
            elif isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")

        print(f"{'='*60}\n")


async def main():
    """Run load tests"""
    print("Cache Load Testing Suite")
    print("="*60)

    # Initialize cache
    print("Initializing cache...")
    try:
        await l1_cache.initialize()
    except Exception as e:
        print(f"Error: Could not connect to Redis: {e}")
        print("Please ensure Redis is running on localhost:6379")
        return

    tester = CacheLoadTester()

    try:
        # Test 1: 1000 concurrent reads
        results = await tester.test_concurrent_reads(
            num_requests=1000,
            num_unique_keys=100
        )
        tester.print_results(results)

        # Test 2: 1000 concurrent writes
        results = await tester.test_concurrent_writes(num_requests=1000)
        tester.print_results(results)

        # Test 3: Mixed workload
        results = await tester.test_mixed_workload(
            num_requests=1000,
            read_ratio=0.8
        )
        tester.print_results(results)

        # Test 4: High concurrency (5000 requests)
        print("\n" + "="*60)
        print("STRESS TEST: 5000 concurrent requests")
        print("="*60)
        results = await tester.test_concurrent_reads(
            num_requests=5000,
            num_unique_keys=500
        )
        tester.print_results(results)

        # Get final cache stats
        print("\n" + "="*60)
        print("FINAL CACHE STATISTICS")
        print("="*60)
        stats = await l1_cache.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")

    finally:
        # Cleanup
        print("\nCleaning up...")
        await l1_cache.shutdown()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
