# FIML Performance Benchmark Results

**Date**: November 22, 2025  
**Version**: 0.1.0  
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
| Parse simple query | 51.77 | 54.38 | 53.30 | 18,389 |
| Parse analyze query | 63.80 | 67.41 | 65.80 | 14,835 |
| Parse compare query | 121.31 | 126.93 | 124.60 | 7,878 |
| Parse find query | 95.21 | 99.38 | 97.32 | 10,062 |
| Parse track query | 94.24 | 99.47 | 97.34 | 10,053 |
| Parser initialization | 27,135.59 | 29,575.74 | 27,527.18 | 34 |
| Parse multiple (5 queries) | 28,050.41 | 29,890.44 | 28,304.23 | 33 |

**Key Insights:**
- Simple queries parse in ~54 microseconds
- Complex queries (COMPARE) take ~127 microseconds
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
