# Performance Testing Quick Reference

## 🚀 Quick Commands

### Setup
```bash
pip install -e ".[dev,performance]"
```

### Performance Tests
```bash
make test-performance              # Quick performance check
make test-performance-full         # Full suite (~15 min)
```

### Load Testing
```bash
make test-load                     # Interactive (web UI at :8089)
make test-load-headless            # Headless 100 users, 5 min
```

### Benchmarking
```bash
pytest benchmarks/ --benchmark-only -v
make benchmark                     # Run benchmarks
make benchmark-save                # Save for comparison
```

### Profiling
```bash
make profile-cache                 # Profile cache operations
make profile-providers             # Profile provider fetches
```

### Regression Detection
```bash
make perf-baseline                 # Create baseline
make perf-compare                  # Compare with baseline
```

### Reports
```bash
make perf-report                   # Generate full report
```

## 📊 Metrics & Targets

| Metric | Target | Test |
|--------|--------|------|
| P95 Latency (cached) | < 200ms | `test_p95_latency_cached_queries` |
| P99 Latency (API) | < 500ms | `test_api_response_time` |
| Cache Hit Rate | > 80% | `test_cache_hit_rate` |
| Task Completion | > 95% | `test_task_completion_rate` |
| System Uptime | > 99.5% | `test_system_uptime_simulation` |

## 🔍 Monitoring Endpoints

```bash
curl http://localhost:8000/health                           # Health check
curl http://localhost:8000/metrics                          # Prometheus metrics
curl http://localhost:8000/api/performance/metrics          # Performance summary
curl http://localhost:8000/api/performance/slow-queries     # Slow queries
```

## 🧪 Test Files

```
tests/performance/
├── load_test.py            # Locust load tests
├── stress_test.py          # Stress & endurance tests  
├── test_targets.py         # Performance target validation
├── regression_detection.py # Regression detection
├── profile.py              # Profiling tools
└── generate_report.py      # Report generation

benchmarks/
├── bench_cache.py          # Cache benchmarks
├── bench_components.py     # Component benchmarks
├── bench_core.py           # Core model benchmarks
└── bench_dsl.py            # DSL benchmarks
```

## 🎯 Load Test Traffic Pattern

- **80%** - Simple price queries (`GET PRICE OF AAPL`)
- **15%** - Deep analysis (narratives, sentiment, fundamentals)
- **5%** - FK-DSL queries (`COMPARE AAPL WITH MSFT`)

## 💡 Common Tasks

### Run Specific Stress Test
```bash
pytest tests/performance/stress_test.py::test_peak_load -v
pytest tests/performance/stress_test.py::test_spike_load -v
pytest tests/performance/stress_test.py::test_endurance -v
```

### Run Specific Benchmark
```bash
pytest benchmarks/bench_components.py::TestCacheBenchmarks --benchmark-only
pytest benchmarks/bench_components.py::TestProviderBenchmarks --benchmark-only
```

### Profile Specific Component
```bash
python tests/performance/profile.py --target cache --duration 30
python tests/performance/profile.py --target providers --duration 30
```

### Custom Profiling
```bash
python tests/performance/profile.py --mode cprofile --code "
import asyncio
from fiml.cache.manager import cache_manager

async def test():
    await cache_manager.initialize()
    # Your code here
    await cache_manager.shutdown()

asyncio.run(test())
"
```

## 🐛 Troubleshooting

### Server Not Running
```bash
python -m fiml.server &
sleep 10  # Wait for startup
```

### Redis/PostgreSQL Issues
```bash
docker-compose up -d redis postgres
# or
make up
```

### View Slow Queries
```bash
curl http://localhost:8000/api/performance/slow-queries | jq
```

### Check Cache Hit Rate
```python
from fiml.monitoring.performance import performance_monitor
metrics = performance_monitor.get_cache_metrics()
print(f"L1 hit rate: {metrics['L1']['hit_rate']:.2%}")
```

## 📈 Grafana Setup

```bash
docker-compose up -d grafana
# Access at http://localhost:3000 (admin/admin)
# Import dashboards from config/grafana/dashboards/
```

## 🔗 Documentation

- **Full Guide**: `docs/development/PERFORMANCE_TESTING.md`
- **Suite README**: `tests/performance/README.md`
- **Implementation Summary**: `PERFORMANCE_SUITE_SUMMARY.md`
- **BLUEPRINT Targets**: `BLUEPRINT.md` (Section 18)

## ⚠️ CI Integration

Performance tests run automatically on:
- ✅ Pull Requests (benchmarks + regression detection)
- ✅ Main branch commits (update baseline)
- ✅ Weekly schedule (full stress tests)

**PR will FAIL if:**
- >10% performance regression detected
- Performance targets not met
- Error rate exceeds thresholds

## 📦 Dependencies

Main dependencies (included in `[performance]`):
- `locust` - Load testing
- `py-spy` - Profiling with flame graphs
- `memory-profiler` - Memory analysis
- `psutil` - System metrics
- `httpx` - Async HTTP testing

## 🎓 Best Practices

1. ✅ Create baseline before optimization
2. ✅ Test incrementally (start low, increase load)
3. ✅ Profile before optimizing
4. ✅ Monitor in production
5. ✅ Document changes

## 📞 Support

- Check `docs/development/PERFORMANCE_TESTING.md`
- Review generated reports in `tests/performance/reports/`
- Check CI logs for automated tests
- Open issue on GitHub

---

**Version**: 1.0  
**Last Updated**: 2025-11-23  
**Maintained By**: FIML Performance Team
