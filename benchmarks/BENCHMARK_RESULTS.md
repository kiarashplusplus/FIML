# FIML Performance Benchmark Results

**Date**: November 22, 2025  
**Version**: 0.1.1  
**Python**: 3.12.3  
**pytest-benchmark**: 5.2.3

## Executive Summary

This document contains baseline performance measurements for FIML core components. All benchmarks are deterministic and run without external dependencies, making them suitable for continuous performance monitoring.

## Benchmark Results

### Core Model Performance (bench_core.py)

| Test | Min (μs) | Mean (μs) | Median (μs) | Ops/sec |
|------|----------|-----------|-------------|---------|
| Asset creation | 1.80 | 1.93 | 1.90 | 516,956 |
| Asset validation | 1.82 | 1.96 | 1.92 | 509,940 |
| Dict conversion | 1.45 | 1.56 | 1.53 | 642,268 |
| JSON serialization | 1.75 | 1.86 | 1.83 | 537,038 |
| Batch creation (10 assets) | 17.42 | 18.10 | 17.90 | 55,255 |
| Crypto asset creation | 1.81 | 1.92 | 1.90 | 519,655 |

**Key Insights:**
- Asset model creation is extremely fast (~2 microseconds)
- JSON serialization adds minimal overhead
- Batch operations scale linearly
- Pydantic validation overhead is negligible

### DSL Parser Performance (bench_dsl.py)

| Test | Min (μs) | Mean (μs) | Median (μs) | Ops/sec |
|------|----------|-----------|-------------|---------|
| Parse with reused parser | 50.50 | 53.55 | 52.45 | 18,674 |
| Parse simple query | 51.80 | 54.53 | 53.39 | 18,338 |
| Parse analyze query | 65.35 | 68.44 | 67.08 | 14,611 |
| Parse compare query | 121.44 | 126.71 | 124.52 | 7,892 |
| Parse find query | 95.70 | 100.26 | 98.38 | 9,974 |
| Parse track query | 95.45 | 100.13 | 97.97 | 9,987 |
| Parser initialization | 27,240.45 | 29,573.33 | 27,601.73 | 34 |
| Parse multiple (5 queries) | 28,309.07 | 30,109.77 | 28,573.90 | 33 |

**Key Insights:**
- Simple queries parse in ~54 microseconds
- Complex queries (COMPARE) take ~127 microseconds
- Parser reuse eliminates ~29ms initialization overhead
- Reusing parser provides identical performance to fresh parser for single queries
- Parser initialization is expensive (~29ms one-time cost)
- Multiple query parsing includes parser initialization overhead
- Lark-based grammar provides good performance for DSL parsing

## Performance Targets vs Actual

| Component | Target | Actual | Status |
|-----------|--------|--------|--------|
| Model Creation | <10μs | ~2μs | ✅ Excellent |
| Model Serialization | <10μs | ~2μs | ✅ Excellent |
| Simple DSL Parsing | <50ms | ~54μs | ✅ Excellent |
| Complex DSL Parsing | <100ms | ~127μs | ✅ Excellent |

All components significantly exceed performance targets.

## Recommendations

### Optimization Opportunities

1. **Parser Reuse**: Parser initialization takes ~29ms. Applications should reuse parser instances rather than recreating for each query.

2. **Batch Operations**: Model creation scales linearly. For large datasets, consider using Pydantic's bulk validation features.

3. **Caching**: For frequently parsed queries, consider implementing a query cache.

### Monitoring

Run benchmarks regularly to detect performance regressions:

```bash
# Save baseline
pytest benchmarks/ --benchmark-only --benchmark-save=baseline

# After changes, compare
pytest benchmarks/ --benchmark-only --benchmark-compare=baseline
```

### Future Benchmarks

Additional benchmarks should be added for:
- Provider operations (requires API keys)
- Arbitration engine (requires provider setup)
- Cache operations (requires Redis/PostgreSQL)
- MCP tools (requires full service stack)
- WebSocket streaming performance

## Environment

- **OS**: Linux
- **Python**: 3.12.3
- **CPU**: (benchmark environment specific)
- **Dependencies**: 
  - pydantic 2.12.4
  - lark 1.3.1
  - pytest-benchmark 5.2.3

## Running Benchmarks

```bash
# Run all benchmarks
make benchmark

# Run with verbose output
pytest benchmarks/ --benchmark-only --benchmark-verbose

# Save results
pytest benchmarks/ --benchmark-only --benchmark-autosave

# Generate histogram
pytest benchmarks/ --benchmark-only --benchmark-histogram
```

---

**Note**: These are baseline measurements on a development environment. Production performance may vary based on hardware, load, and concurrent operations.
