# Performance Testing Guide

This guide explains how to run performance tests, load tests, and benchmarks for the FIML system.

## Overview

The performance testing suite includes:

1. **Load Testing** - Simulate concurrent users and realistic traffic patterns
2. **Stress Testing** - Test system behavior under extreme conditions
3. **Benchmarking** - Measure component-level performance
4. **Performance Monitoring** - Track metrics in real-time
5. **Regression Detection** - Detect performance regressions in PRs
6. **Profiling** - Identify performance bottlenecks

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -e ".[dev]"

# Install additional performance testing tools
pip install locust py-spy memory-profiler psutil httpx
```

### Run All Tests

```bash
# Run quick performance check
make test-performance

# Run full performance suite (takes ~15 minutes)
make test-performance-full
```

## Load Testing

### Using Locust

Locust provides a web UI for interactive load testing.

```bash
# Start Locust web UI
locust -f tests/performance/load_test.py --host=http://localhost:8000

# Then open http://localhost:8089 in your browser
# Set number of users and spawn rate, then start test
```

### Headless Load Testing

Run load tests without the web UI:

```bash
# 100 users, 5 minute test
locust -f tests/performance/load_test.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html tests/performance/reports/load_test_report.html

# High load (500 users)
locust -f tests/performance/load_test.py \
    --host=http://localhost:8000 \
    --users 500 \
    --spawn-rate 50 \
    --run-time 10m \
    --headless
```

### Load Test Scenarios

The load tests simulate realistic traffic:

- **80%** - Simple price queries
- **15%** - Deep analysis (narratives, sentiment)
- **5%** - FK-DSL queries

### Interpreting Results

After running, check:

- **Response Times**: P50, P95, P99 latencies
- **Throughput**: Requests per second
- **Error Rate**: Should be < 1%
- **Cache Hit Rate**: Should be > 80%

## Stress Testing

Test system behavior under extreme conditions:

```bash
# Peak load test (2x normal traffic)
pytest tests/performance/stress_test.py::test_peak_load -v

# Spike test (sudden 10x load)
pytest tests/performance/stress_test.py::test_spike_load -v

# Endurance test (1 hour sustained load)
pytest tests/performance/stress_test.py::test_endurance -v

# Failure scenarios
pytest tests/performance/stress_test.py::test_provider_failure -v
pytest tests/performance/stress_test.py::test_database_connection_pool_exhaustion -v
pytest tests/performance/stress_test.py::test_redis_max_connections -v
pytest tests/performance/stress_test.py::test_memory_leak_detection -v
```

### Stress Test Targets

- Peak load: < 5% error rate
- Spike load: < 10% error rate
- Endurance: No performance degradation over time
- Failure scenarios: Graceful degradation

## Benchmarking

### Component Benchmarks

```bash
# Run all benchmarks
pytest benchmarks/ --benchmark-only -v

# Specific component
pytest benchmarks/bench_cache.py --benchmark-only
pytest benchmarks/bench_components.py::TestProviderBenchmarks --benchmark-only

# Save results for comparison
pytest benchmarks/ --benchmark-only --benchmark-json=benchmark_results.json

# Compare with baseline
pytest benchmarks/ --benchmark-only --benchmark-compare=baseline.json
```

### Performance Targets

Component benchmarks validate these targets:

| Component | Target |
|-----------|--------|
| L1 Cache GET | < 100ms |
| L2 Cache GET | < 700ms |
| Provider Fetch | < 2s |
| Narrative Generation | < 3s |
| DSL Execution | < 1s |
| Agent Processing | < 2s |

## Performance Monitoring

### Real-Time Monitoring

```bash
# Start server with monitoring
python -m fiml.server

# View Prometheus metrics
curl http://localhost:8000/metrics

# View performance dashboard
curl http://localhost:8000/api/performance/metrics
```

### Metrics Available

- **Request Metrics**: Count, duration, status codes
- **Cache Metrics**: Hit rate, latency, operations
- **Provider Metrics**: Request count, latency, errors
- **Task Metrics**: Completion rate
- **Slow Queries**: Queries > 1 second

### Grafana Dashboard

```bash
# Start Grafana (if using docker-compose)
docker-compose up -d grafana

# Access at http://localhost:3000
# Import dashboard from config/grafana/dashboards/
```

## Performance Targets Tests

Run tests that validate BLUEPRINT targets:

```bash
# All performance targets
pytest tests/performance/test_targets.py -v

# Specific target
pytest tests/performance/test_targets.py::TestPerformanceTargets::test_p95_latency_cached_queries -v
pytest tests/performance/test_targets.py::TestPerformanceTargets::test_cache_hit_rate -v
```

### Targets

- ✅ P95 latency < 200ms for cached queries
- ✅ Cache hit rate > 80%
- ✅ Task completion rate > 95%
- ✅ Uptime > 99.5%

**These tests FAIL the CI build if targets are not met.**

## Regression Detection

### In Development

```bash
# Create baseline from main branch
git checkout main
python tests/performance/regression_detection.py --save-baseline

# Compare current branch
git checkout feature-branch
python tests/performance/regression_detection.py \
    --baseline benchmark_baseline.json \
    --threshold 0.10 \
    --report regression_report.txt
```

### In CI

```bash
# Run regression detection (fails on >10% regression)
python tests/performance/regression_detection.py \
    --baseline benchmarks/baseline.json \
    --ci \
    --threshold 0.10
```

This is integrated into the CI pipeline to prevent performance regressions from merging.

## Profiling

### Profile Cache Operations

```bash
python tests/performance/profile.py --target cache --duration 30
```

### Profile Provider Fetches

```bash
python tests/performance/profile.py --target providers --duration 30
```

### Profile Running Server

```bash
# Find server process ID
ps aux | grep "fiml.server"

# Profile with py-spy
python tests/performance/profile.py --mode pyspy --pid <PID> --duration 60
```

### Profile Custom Code

```bash
python tests/performance/profile.py --mode cprofile --code "
import asyncio
from fiml.cache.manager import cache_manager

async def test():
    await cache_manager.initialize()
    # ... your code ...
    await cache_manager.shutdown()

asyncio.run(test())
"
```

### Analyze Results

Profiling results are saved to `profiling_results/`:

- `cprofile_*.stats` - cProfile statistics
- `cprofile_*.txt` - Human-readable report
- `pyspy_*.svg` - Flame graphs (open in browser)
- `summary_*.txt` - Summary report

## Performance Reports

### Generate Report

```bash
# Generate comprehensive performance report
python tests/performance/generate_report.py --output PERFORMANCE_REPORT.md
```

The report includes:

- Executive summary
- BLUEPRINT targets comparison
- Cache performance analysis
- Slow query analysis
- Bottleneck identification
- Optimization recommendations
- Next steps

### Automated Reports

Reports are automatically generated:

- After each performance test run
- On each PR (CI)
- Weekly (scheduled)

## CI Integration

### GitHub Actions

```yaml
name: Performance Tests

on:
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run benchmarks
        run: |
          pytest benchmarks/ --benchmark-only --benchmark-json=benchmark_results.json
      
      - name: Detect regressions
        run: |
          python tests/performance/regression_detection.py \
            --baseline benchmarks/baseline.json \
            --ci \
            --threshold 0.10
      
      - name: Performance targets
        run: |
          pytest tests/performance/test_targets.py -v
      
      - name: Generate report
        if: always()
        run: |
          python tests/performance/generate_report.py
      
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: PERFORMANCE_REPORT.md
```

## Troubleshooting

### Load Tests Failing

1. Check if server is running: `curl http://localhost:8000/health`
2. Review error logs in `logs/`
3. Check system resources: `top`, `df -h`
4. Verify database/Redis are accessible

### Low Cache Hit Rate

1. Check cache configuration in `.env`
2. Verify Redis is running: `redis-cli ping`
3. Review cache TTL settings
4. Check for cache key collisions

### Slow Queries

1. Review slow query log: `curl http://localhost:8000/api/performance/slow-queries`
2. Check database indexes
3. Analyze query plans: `EXPLAIN ANALYZE`
4. Profile with `profile.py`

### Memory Leaks

1. Run memory leak detection: `pytest tests/performance/stress_test.py::test_memory_leak_detection`
2. Profile memory: `python tests/performance/profile.py --mode memory`
3. Check for circular references
4. Review cache cleanup

## Best Practices

1. **Run Baseline Tests**
   - Always create baseline before optimization
   - Compare before/after metrics

2. **Test Incrementally**
   - Start with low load
   - Gradually increase
   - Monitor system resources

3. **Monitor in Production**
   - Set up Grafana dashboards
   - Configure alerts
   - Review metrics weekly

4. **Optimize Gradually**
   - Profile first, optimize second
   - One optimization at a time
   - Measure impact

5. **Document Changes**
   - Record optimization attempts
   - Track performance over time
   - Update baselines

## Additional Resources

- [BLUEPRINT.md](https://github.com/kiarashplusplus/FIML/blob/main/BLUEPRINT.md) - Performance targets
- [Locust Documentation](https://docs.locust.io/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Python Profiling](https://docs.python.org/3/library/profile.html)

## Support

For issues or questions:

1. Check existing documentation
2. Review performance reports
3. Check CI logs
4. Open an issue on GitHub
