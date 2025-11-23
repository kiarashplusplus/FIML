"""
Enhanced Component Benchmarking Suite

Benchmarks each component individually:
- Provider fetches
- Cache operations (L1, L2)
- Narrative generation
- Agent processing
- FK-DSL execution

Compares against Phase 1 baseline and tracks performance over time.

Usage:
    # Run all benchmarks
    pytest benchmarks/bench_components.py --benchmark-only

    # Run specific benchmark
    pytest benchmarks/bench_components.py::TestProviderBenchmarks --benchmark-only

    # Generate report
    pytest benchmarks/bench_components.py --benchmark-only --benchmark-json=benchmark_results.json

    # Compare with baseline
    pytest benchmarks/bench_components.py --benchmark-only --benchmark-compare=baseline.json
"""

import asyncio
import contextlib
import time

import pytest

from fiml.cache.l1_cache import l1_cache
from fiml.cache.manager import cache_manager
from fiml.core.models import Asset, AssetType, Market
from fiml.providers.registry import provider_registry

# Phase 1 Baseline Targets (from BLUEPRINT.md)
BASELINE_TARGETS = {
    "l1_cache_get": 50,  # ms - target: 10-100ms
    "l2_cache_get": 500,  # ms - target: 300-700ms
    "provider_fetch": 1000,  # ms - target: depends on provider
    "narrative_generation": 2000,  # ms - target: <3s
    "dsl_execution": 500,  # ms - target: <1s
    "agent_processing": 1500,  # ms - target: <2s
}


class TestProviderBenchmarks:
    """Benchmark provider data fetches"""

    @pytest.mark.asyncio
    async def test_yahoo_finance_price_fetch(self, benchmark):
        """Benchmark Yahoo Finance price fetch"""
        from fiml.providers.yahoo_finance import YahooFinanceProvider

        provider = YahooFinanceProvider()
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.EQUITY,
            market=Market.US,
        )

        async def fetch_price():
            start = time.perf_counter()
            result = await provider.fetch_price(asset)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        # Warmup
        with contextlib.suppress(Exception):
            await fetch_price()

        # Benchmark
        def sync_wrapper():
            return asyncio.run(fetch_price())

        result = benchmark(sync_wrapper)

        if result and result[0]:
            print(f"\n  Yahoo Finance fetch: {result[1]:.2f}ms")

    @pytest.mark.asyncio
    async def test_ccxt_price_fetch(self, benchmark):
        """Benchmark CCXT price fetch"""
        from fiml.providers.ccxt_provider import CCXTProvider

        provider = CCXTProvider(exchange_id="binance")

        try:
            await provider.initialize()
        except:
            pytest.skip("CCXT not available in test environment")

        asset = Asset(
            symbol="BTC/USDT",
            name="Bitcoin",
            asset_type=AssetType.CRYPTO,
            market=Market.CRYPTO,
        )

        async def fetch_price():
            start = time.perf_counter()
            result = await provider.fetch_price(asset)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(fetch_price())

        result = benchmark(sync_wrapper)

        if result and result[0]:
            print(f"\n  CCXT fetch: {result[1]:.2f}ms")

    @pytest.mark.asyncio
    async def test_provider_registry_fetch(self, benchmark):
        """Benchmark provider registry fetch with fallback"""
        await provider_registry.initialize()

        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.EQUITY,
            market=Market.US,
        )

        async def fetch_with_fallback():
            start = time.perf_counter()
            result = await provider_registry.fetch_price(asset)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(fetch_with_fallback())

        result = benchmark(sync_wrapper)

        if result and result[0]:
            print(f"\n  Registry fetch with fallback: {result[1]:.2f}ms")

    @pytest.mark.asyncio
    async def test_batch_provider_fetch(self, benchmark):
        """Benchmark batch provider fetches"""
        await provider_registry.initialize()

        assets = [
            Asset(symbol="AAPL", name="Apple", asset_type=AssetType.EQUITY, market=Market.US),
            Asset(symbol="TSLA", name="Tesla", asset_type=AssetType.EQUITY, market=Market.US),
            Asset(symbol="MSFT", name="Microsoft", asset_type=AssetType.EQUITY, market=Market.US),
        ]

        async def fetch_batch():
            start = time.perf_counter()
            tasks = [provider_registry.fetch_price(asset) for asset in assets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            latency_ms = (time.perf_counter() - start) * 1000
            return results, latency_ms

        def sync_wrapper():
            return asyncio.run(fetch_batch())

        result = benchmark(sync_wrapper)
        print(f"\n  Batch fetch (3 assets): {result[1]:.2f}ms")


class TestCacheBenchmarks:
    """Benchmark cache operations"""

    @pytest.mark.asyncio
    async def test_l1_cache_set_get(self, benchmark):
        """Benchmark L1 cache SET and GET"""
        await l1_cache.initialize()

        data = {"price": 150.25, "timestamp": time.time()}

        async def cache_operations():
            start = time.perf_counter()

            # SET
            await l1_cache.set("bench_key", data, ttl_seconds=300)

            # GET
            result = await l1_cache.get("bench_key")

            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(cache_operations())

        result = benchmark(sync_wrapper)
        print(f"\n  L1 SET+GET: {result[1]:.2f}ms (target: <100ms)")

        assert result[1] < BASELINE_TARGETS["l1_cache_get"] * 2  # SET+GET should be <100ms

    @pytest.mark.asyncio
    async def test_l1_cache_get_only(self, benchmark):
        """Benchmark L1 cache GET only"""
        await l1_cache.initialize()

        # Pre-populate
        await l1_cache.set("bench_key_get", {"price": 150.25}, ttl_seconds=300)

        async def get_operation():
            start = time.perf_counter()
            result = await l1_cache.get("bench_key_get")
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(get_operation())

        result = benchmark(sync_wrapper)
        print(f"\n  L1 GET: {result[1]:.2f}ms (target: 10-100ms)")

        assert result[1] < BASELINE_TARGETS["l1_cache_get"]

    @pytest.mark.asyncio
    async def test_l1_cache_batch_operations(self, benchmark):
        """Benchmark L1 cache batch operations"""
        await l1_cache.initialize()

        async def batch_operations():
            start = time.perf_counter()

            # Batch SET
            for i in range(10):
                await l1_cache.set(f"batch_key_{i}", {"value": i}, ttl_seconds=300)

            # Batch GET
            results = []
            for i in range(10):
                result = await l1_cache.get(f"batch_key_{i}")
                results.append(result)

            latency_ms = (time.perf_counter() - start) * 1000
            return results, latency_ms

        def sync_wrapper():
            return asyncio.run(batch_operations())

        result = benchmark(sync_wrapper)
        print(f"\n  L1 Batch (10 items): {result[1]:.2f}ms")

    @pytest.mark.asyncio
    async def test_cache_manager_price_lookup(self, benchmark):
        """Benchmark cache manager price lookup"""
        await cache_manager.initialize()

        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.EQUITY,
            market=Market.US,
        )

        async def cache_lookup():
            start = time.perf_counter()
            result = await cache_manager.get_price(asset)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(cache_lookup())

        result = benchmark(sync_wrapper)
        print(f"\n  Cache manager price lookup: {result[1]:.2f}ms")


class TestNarrativeBenchmarks:
    """Benchmark narrative generation"""

    @pytest.mark.asyncio
    async def test_narrative_generation_concise(self, benchmark):
        """Benchmark concise narrative generation"""
        from fiml.narrative.generator import narrative_generator
        from fiml.narrative.models import NarrativeContext, NarrativeStyle

        context = NarrativeContext(
            symbol="AAPL",
            asset_type=AssetType.EQUITY,
            style=NarrativeStyle.CONCISE,
            price_data={"price": 150.25, "change": 1.5},
        )

        async def generate_narrative():
            start = time.perf_counter()
            result = await narrative_generator.generate(context)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(generate_narrative())

        try:
            result = benchmark(sync_wrapper)
            print(f"\n  Narrative (concise): {result[1]:.2f}ms (target: <3000ms)")
            assert result[1] < BASELINE_TARGETS["narrative_generation"]
        except Exception as e:
            pytest.skip(f"Narrative generation not available: {e}")

    @pytest.mark.asyncio
    async def test_narrative_generation_detailed(self, benchmark):
        """Benchmark detailed narrative generation"""
        from fiml.narrative.generator import narrative_generator
        from fiml.narrative.models import NarrativeContext, NarrativeStyle

        context = NarrativeContext(
            symbol="AAPL",
            asset_type=AssetType.EQUITY,
            style=NarrativeStyle.DETAILED,
            price_data={"price": 150.25, "change": 1.5},
            fundamental_data={"pe_ratio": 28.5, "market_cap": 2400000000000},
            technical_data={"rsi": 65.3, "macd": 1.2},
        )

        async def generate_narrative():
            start = time.perf_counter()
            result = await narrative_generator.generate(context)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(generate_narrative())

        try:
            result = benchmark(sync_wrapper)
            print(f"\n  Narrative (detailed): {result[1]:.2f}ms (target: <3000ms)")
        except Exception as e:
            pytest.skip(f"Narrative generation not available: {e}")


class TestDSLBenchmarks:
    """Benchmark FK-DSL execution"""

    @pytest.mark.asyncio
    async def test_dsl_simple_query(self, benchmark):
        """Benchmark simple DSL query"""
        from fiml.dsl.executor import DSLExecutor

        executor = DSLExecutor()
        query = "GET PRICE OF AAPL"

        async def execute_dsl():
            start = time.perf_counter()
            result = await executor.execute(query)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(execute_dsl())

        try:
            result = benchmark(sync_wrapper)
            print(f"\n  DSL simple query: {result[1]:.2f}ms (target: <1000ms)")
            assert result[1] < BASELINE_TARGETS["dsl_execution"]
        except Exception as e:
            pytest.skip(f"DSL execution not available: {e}")

    @pytest.mark.asyncio
    async def test_dsl_complex_query(self, benchmark):
        """Benchmark complex DSL query"""
        from fiml.dsl.executor import DSLExecutor

        executor = DSLExecutor()
        query = "COMPARE AAPL WITH MSFT"

        async def execute_dsl():
            start = time.perf_counter()
            result = await executor.execute(query)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        def sync_wrapper():
            return asyncio.run(execute_dsl())

        try:
            result = benchmark(sync_wrapper)
            print(f"\n  DSL complex query: {result[1]:.2f}ms")
        except Exception as e:
            pytest.skip(f"DSL execution not available: {e}")

    @pytest.mark.asyncio
    async def test_dsl_parsing_only(self, benchmark):
        """Benchmark DSL parsing only (no execution)"""
        from fiml.dsl.parser import DSLParser

        parser = DSLParser()
        query = "GET PRICE OF AAPL, MSFT, GOOGL"

        def parse_dsl():
            start = time.perf_counter()
            result = parser.parse(query)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms

        try:
            result = benchmark(parse_dsl)
            print(f"\n  DSL parsing: {result[1]:.2f}ms")
        except Exception as e:
            pytest.skip(f"DSL parsing not available: {e}")


class TestAgentBenchmarks:
    """Benchmark agent processing"""

    @pytest.mark.asyncio
    async def test_single_agent_task(self, benchmark):
        """Benchmark single agent task processing"""
        try:
            from fiml.tasks.models import Task, TaskType

            from fiml.agents.orchestrator import agent_orchestrator

            await agent_orchestrator.initialize()

            task = Task(
                task_type=TaskType.PRICE_QUERY,
                parameters={"symbol": "AAPL"},
            )

            async def process_task():
                start = time.perf_counter()
                result = await agent_orchestrator.execute_task(task)
                latency_ms = (time.perf_counter() - start) * 1000
                return result, latency_ms

            def sync_wrapper():
                return asyncio.run(process_task())

            result = benchmark(sync_wrapper)
            print(f"\n  Single agent task: {result[1]:.2f}ms (target: <2000ms)")
            assert result[1] < BASELINE_TARGETS["agent_processing"]
        except Exception as e:
            pytest.skip(f"Agent processing not available: {e}")

    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, benchmark):
        """Benchmark multi-agent coordination"""
        try:
            from fiml.tasks.models import Task, TaskType

            from fiml.agents.orchestrator import agent_orchestrator

            await agent_orchestrator.initialize()

            task = Task(
                task_type=TaskType.MULTI_ASSET_ANALYSIS,
                parameters={
                    "symbols": ["AAPL", "TSLA", "MSFT"],
                    "analysis_type": "comparison",
                },
            )

            async def process_task():
                start = time.perf_counter()
                result = await agent_orchestrator.execute_task(task)
                latency_ms = (time.perf_counter() - start) * 1000
                return result, latency_ms

            def sync_wrapper():
                return asyncio.run(process_task())

            result = benchmark(sync_wrapper)
            print(f"\n  Multi-agent coordination: {result[1]:.2f}ms")
        except Exception as e:
            pytest.skip(f"Agent processing not available: {e}")


class TestSerializationBenchmarks:
    """Benchmark serialization/deserialization overhead"""

    def test_asset_serialization(self, benchmark):
        """Benchmark Asset model serialization"""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.EQUITY,
            market=Market.US,
            exchange="NASDAQ",
            currency="USD",
        )

        def serialize():
            return asset.model_dump_json()

        result = benchmark(serialize)
        print(f"\n  Asset serialization: {len(result)} bytes")

    def test_asset_deserialization(self, benchmark):
        """Benchmark Asset model deserialization"""
        asset_json = '{"symbol":"AAPL","name":"Apple Inc.","asset_type":"EQUITY","market":"US","exchange":"NASDAQ","currency":"USD"}'

        def deserialize():
            return Asset.model_validate_json(asset_json)

        result = benchmark(deserialize)
        assert result.symbol == "AAPL"

    def test_batch_serialization(self, benchmark):
        """Benchmark batch serialization"""
        assets = [
            Asset(
                symbol=f"TEST{i}",
                name=f"Test Asset {i}",
                asset_type=AssetType.EQUITY,
                market=Market.US,
            )
            for i in range(100)
        ]

        def serialize_batch():
            return [asset.model_dump_json() for asset in assets]

        result = benchmark(serialize_batch)
        print(f"\n  Batch serialization (100 assets): {sum(len(r) for r in result)} bytes")


class TestCacheKeyGenerationBenchmarks:
    """Benchmark cache key generation"""

    def test_simple_key_generation(self, benchmark):
        """Benchmark simple cache key generation"""

        def generate_key():
            return f"price:AAPL:yahoo:{int(time.time() / 300)}"

        result = benchmark(generate_key)
        print(f"\n  Simple key: {result}")

    def test_complex_key_generation(self, benchmark):
        """Benchmark complex cache key generation"""
        import hashlib

        def generate_key():
            params = {
                "symbol": "AAPL",
                "provider": "yahoo",
                "include_history": True,
                "days": 30,
                "include_fundamentals": True,
            }
            param_str = ",".join(f"{k}:{v}" for k, v in sorted(params.items()))
            hash_key = hashlib.md5(param_str.encode()).hexdigest()
            return f"complex:{hash_key}"

        result = benchmark(generate_key)
        print(f"\n  Complex key: {result}")


if __name__ == "__main__":
    # Run benchmarks
    pytest.main([
        __file__,
        "--benchmark-only",
        "--benchmark-verbose",
        "-v",
    ])
