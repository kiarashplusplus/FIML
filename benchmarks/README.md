# FIML Performance Benchmarks

This directory contains performance benchmarks for critical FIML components using `pytest-benchmark`.

## Overview

The benchmarks measure performance across key system components:

- **Core Models**: Pydantic model creation, validation, and serialization
- **DSL Parser**: FK-DSL query parsing for different query types

## Running Benchmarks

### Run all benchmarks

```bash
make benchmark
```

or

```bash
pytest benchmarks/ --benchmark-only
```

### Run specific benchmark file

```bash
pytest benchmarks/bench_dsl.py --benchmark-only
pytest benchmarks/bench_core.py --benchmark-only
```

### Run with detailed statistics

```bash
pytest benchmarks/ --benchmark-only --benchmark-verbose
```

### Save benchmark results

```bash
pytest benchmarks/ --benchmark-only --benchmark-autosave
```

### Compare benchmark results

```bash
# Run and save first set
pytest benchmarks/ --benchmark-only --benchmark-save=baseline

# Make changes to code

# Run and compare with baseline
pytest benchmarks/ --benchmark-only --benchmark-compare=baseline
```

## Benchmark Options

### Common pytest-benchmark options:

- `--benchmark-only`: Run only benchmarks (skip regular tests)
- `--benchmark-skip`: Skip benchmarks (run only regular tests)
- `--benchmark-verbose`: Show more detailed output
- `--benchmark-autosave`: Automatically save results
- `--benchmark-save=NAME`: Save results with a specific name
- `--benchmark-compare=NAME`: Compare with saved results
- `--benchmark-min-rounds=N`: Minimum number of rounds (default: 5)
- `--benchmark-warmup=on/off`: Enable/disable warmup rounds

### Generate HTML report

```bash
pytest benchmarks/ --benchmark-only --benchmark-autosave --benchmark-histogram
```

## Performance Targets

Based on FIML architecture requirements:

| Component | Target | Notes |
|-----------|--------|-------|
| DSL Parsing | <50ms | Simple queries should parse in microseconds |
| Model Creation | <10μs | Pydantic models should be fast |
| Model Serialization | <10μs | JSON serialization should be efficient |

Run benchmarks to establish baselines and track performance over time.

## Current Benchmarks

### bench_core.py
Tests core Pydantic model performance:
- Asset model creation and validation
- Dict and JSON serialization
- Batch operations

### bench_dsl.py
Tests FK-DSL parser performance:
- Simple and complex query parsing
- GET, ANALYZE, COMPARE, FIND, TRACK queries
- Parser initialization overhead
- Multiple query parsing

## Benchmark Structure

Each benchmark file follows this pattern:

```python
class TestComponentBenchmarks:
    """Benchmarks for Component"""

    def test_operation(self, benchmark, fixture):
        """Benchmark description"""
        
        def operation():
            # Code to benchmark
            return result
        
        result = benchmark(operation)
        assert result is not None
```

For async operations:

```python
@pytest.mark.asyncio
async def test_async_operation(self, benchmark, fixture):
    """Benchmark async operation"""
    
    async def operation():
        return await some_async_call()
    
    result = await benchmark.pedantic(operation, rounds=10)
    assert result is not None
```

## Continuous Integration

Benchmarks are designed to run in CI but are separated from regular tests to avoid impacting test suite runtime. They can be run periodically to track performance trends.

## Adding New Benchmarks

1. Create a new file `bench_<component>.py` in the benchmarks directory
2. Import required modules and fixtures from `conftest.py`
3. Follow the naming convention: `test_<operation>_<scenario>`
4. Add appropriate assertions to verify correctness
5. Document expected performance targets in comments
6. Update this README with new benchmark information

## Notes

- Benchmarks focus on measuring FIML logic performance
- External dependencies are avoided to make benchmarks deterministic
- Async benchmarks use `benchmark.pedantic()` for proper async handling
- All benchmarks should be deterministic and repeatable
- For components requiring external services (providers, cache, etc.), consider using mocks or skip benchmarks if dependencies aren't available
