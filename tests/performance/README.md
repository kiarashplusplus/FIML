# Performance Testing Suite

Comprehensive performance testing and optimization framework for FIML.

## 📊 Overview

This suite provides complete performance testing capabilities including:

- **Load Testing** - Simulate realistic user traffic with Locust
- **Stress Testing** - Test system limits and failure scenarios  
- **Benchmarking** - Measure component-level performance
- **Performance Monitoring** - Real-time metrics with Prometheus
- **Regression Detection** - Prevent performance degradation in PRs
- **Profiling** - Identify and analyze bottlenecks
- **Automated Reporting** - Comprehensive performance reports

## 🚀 Quick Start

```bash
# Install dependencies
pip install -e ".[dev,performance]"

# Run performance target tests
make test-performance

# Run load test (interactive)
make test-load

# Generate performance report
make perf-report
```

## 📁 Structure

```
tests/performance/
├── __init__.py                    # Package init
├── conftest.py                    # Pytest configuration
├── load_test.py                   # Locust load tests
├── stress_test.py                 # Stress and endurance tests
├── test_targets.py                # Performance target validation
├── regression_detection.py        # Detect regressions
├── profile.py                     # Profiling tools
├── generate_report.py             # Report generation
└── reports/                       # Generated reports

benchmarks/
├── bench_cache.py                 # Cache benchmarks
├── bench_components.py            # Component benchmarks
├── bench_core.py                  # Core model benchmarks
├── bench_dsl.py                   # DSL benchmarks
└── baseline.json                  # Performance baseline

fiml/monitoring/
├── __init__.py
└── performance.py                 # Performance monitoring
```

## 🎯 Performance Targets

From BLUEPRINT.md Section 18:

| Metric | Target | Status |
|--------|--------|--------|
| Avg Response Time | < 200ms | ⚠️ |
| P99 Latency | < 500ms | ⚠️ |
| Cache Hit Rate | > 80% | ⚠️ |
| Task Completion Rate | > 95% | ⚠️ |
| System Uptime | > 99.5% | ⚠️ |
| Provider Uptime | > 99% | ⚠️ |

**All targets are tested in CI and will fail the build if not met.**

## 🧪 Test Types

### 1. Load Testing

Simulates concurrent users with realistic traffic patterns:

```bash
# Interactive (web UI)
locust -f tests/performance/load_test.py --host=http://localhost:8000

# Headless (100 users, 5 minutes)
make test-load-headless
```

**Traffic Distribution:**
- 80% - Simple price queries
- 15% - Deep analysis (narratives, sentiment)
- 5% - FK-DSL queries

### 2. Stress Testing

Tests system behavior under extreme conditions:

```bash
# Peak load (2x normal)
pytest tests/performance/stress_test.py::test_peak_load -v

# Spike test (10x sudden load)
pytest tests/performance/stress_test.py::test_spike_load -v

# Endurance (1 hour sustained)
pytest tests/performance/stress_test.py::test_endurance -v
```

### 3. Benchmarking

Measures component-level performance:

```bash
# All benchmarks
pytest benchmarks/ --benchmark-only -v

# Specific component
pytest benchmarks/bench_cache.py --benchmark-only

# Save baseline
make benchmark-save
```

### 4. Performance Targets

Validates BLUEPRINT targets:

```bash
# All targets
pytest tests/performance/test_targets.py -v

# Specific target
pytest tests/performance/test_targets.py::test_p95_latency_cached_queries -v
```

### 5. Regression Detection

Compares performance between branches:

```bash
# Create baseline
make perf-baseline

# Compare with baseline
make perf-compare
```

### 6. Profiling

Identifies performance bottlenecks:

```bash
# Profile cache
make profile-cache

# Profile providers
make profile-providers

# Custom profiling
python tests/performance/profile.py --mode cprofile --target cache
```

## 📈 Performance Monitoring

### Real-Time Metrics

```bash
# Start server with monitoring
python -m fiml.server

# View Prometheus metrics
curl http://localhost:8000/metrics

# Performance dashboard
curl http://localhost:8000/api/performance/metrics
```

### Available Metrics

- **Request Metrics**: Count, duration, status codes
- **Cache Metrics**: Hit rate, latency, operations
- **Provider Metrics**: Request count, latency, errors
- **Task Metrics**: Completion rate
- **Slow Queries**: Queries > 1 second

### Grafana Dashboards

```bash
# Start Grafana
docker-compose up -d grafana

# Access at http://localhost:3000
# Default credentials: admin/admin
```

## 📊 Reports

### Generate Performance Report

```bash
make perf-report
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

Reports are generated:
- After each performance test run
- On each PR (CI)
- Weekly (scheduled)

## 🔧 CI Integration

### GitHub Actions

See `.github/workflows/performance.yml.example` for full workflow.

**On Pull Request:**
- Run benchmarks
- Compare with baseline
- Detect regressions (>10%)
- Run performance target tests
- Comment PR with results

**On Main Branch:**
- Update performance baseline
- Run full stress tests
- Generate reports

**Scheduled (Weekly):**
- Full performance test suite
- Long-running endurance tests
- Generate trend reports

## 📚 Documentation

- [Performance Testing Guide](../../docs/development/PERFORMANCE_TESTING.md) - Complete guide
- [BLUEPRINT.md](../../BLUEPRINT.md) - Performance targets
- [Makefile](../../Makefile) - Available commands

## 🐛 Troubleshooting

### Low Cache Hit Rate

1. Check Redis connection
2. Review cache TTL settings
3. Verify cache key generation
4. Check for cache key collisions

### Slow Queries

1. Review slow query log
2. Check database indexes
3. Analyze query plans
4. Profile with cProfile

### Memory Leaks

1. Run memory leak detection
2. Profile with memory-profiler
3. Check for circular references
4. Review cache cleanup

## 🎓 Best Practices

1. **Always create baseline** before optimization
2. **Test incrementally** - start with low load
3. **Monitor in production** with Grafana
4. **Optimize gradually** - profile first
5. **Document changes** and track trends

## 📞 Support

- Check [documentation](../../docs/development/PERFORMANCE_TESTING.md)
- Review [performance reports](./reports/)
- Check CI logs
- Open an issue on GitHub

## 🔗 Related

- [Locust Documentation](https://docs.locust.io/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Python Profiling](https://docs.python.org/3/library/profile.html)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
