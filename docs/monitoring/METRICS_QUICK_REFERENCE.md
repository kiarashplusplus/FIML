# FIML Metrics & Analytics - Quick Reference

## Quick Start

```bash
# Start all services
docker-compose up -d

# Access services
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9091
- FIML Metrics: http://localhost:8000/metrics
```

## Available Dashboards

| Dashboard | UID | Port | Purpose |
|-----------|-----|------|---------|
| System Overview | `fiml-overview` | :3000 | High-level health & performance |
| Cache Analytics | `fiml-cache-analytics` | :3000 | Cache performance & optimization |
| Session Analytics | `fiml-session-analytics` | :3000 | User behavior & patterns |
| Watchdog Health | `fiml-watchdog-health` | :3000 | Monitoring system status |
| API Metrics | `fiml-api-metrics` | :3000 | Request/response performance |

## Metrics Endpoints

### Prometheus Format
```bash
# All Prometheus metrics
curl http://localhost:8000/metrics
```

### JSON Format
```bash
# Cache analytics
curl http://localhost:8000/api/metrics/cache | jq

# Watchdog health
curl http://localhost:8000/api/metrics/watchdog | jq

# Performance stats
curl http://localhost:8000/api/metrics/performance | jq

# Task registry
curl http://localhost:8000/api/metrics/tasks | jq
```

## Key Metrics by Component

### Cache
- `fiml_cache_hits_total` - Total cache hits
- `fiml_cache_misses_total` - Total cache misses
- `fiml_cache_latency_seconds` - Cache operation latency
- `fiml_cache_hit_rate` - Hit rate percentage
- `fiml_cache_evictions_total` - Evictions count

### Sessions
- `fiml_sessions_active_total` - Active sessions
- `fiml_sessions_created_total` - Sessions created
- `fiml_session_duration_seconds` - Session duration
- `fiml_sessions_abandoned_total` - Abandoned sessions
- `fiml_session_queries_total` - Queries per session

### Watchdogs
- `fiml_watchdog_healthy_count` - Healthy watchdogs
- `fiml_watchdog_unhealthy_count` - Unhealthy watchdogs
- `fiml_watchdog_checks_total` - Total checks
- `fiml_watchdog_events_detected_total` - Events detected
- `fiml_watchdog_check_duration_seconds` - Check duration

### Performance
- `fiml_requests_total` - Total requests
- `fiml_request_duration_seconds` - Request duration
- `fiml_active_requests` - Active requests
- `fiml_slow_queries_total` - Slow queries
- `fiml_task_completion_rate` - Task completion rate

### Providers
- `fiml_provider_requests_total` - Provider API calls
- `fiml_provider_latency_seconds` - Provider latency

### Narrative
- `fiml_narrative_generation_seconds` - Generation time
- `fiml_dsl_execution_seconds` - DSL execution time

## Useful PromQL Queries

### Cache Hit Rate
```promql
100 * sum(rate(fiml_cache_hits_total[5m])) / 
  (sum(rate(fiml_cache_hits_total[5m])) + sum(rate(fiml_cache_misses_total[5m])))
```

### Request Rate by Status
```promql
sum(rate(fiml_requests_total[5m])) by (status)
```

### p95 Request Latency
```promql
histogram_quantile(0.95, rate(fiml_request_duration_seconds_bucket[5m]))
```

### Average Session Duration
```promql
avg(fiml_session_duration_seconds)
```

### Watchdog Success Rate
```promql
fiml_watchdog_success_rate
```

## Alerting Examples

### High Cache Miss Rate
```yaml
- alert: HighCacheMissRate
  expr: |
    100 * (sum(rate(fiml_cache_misses_total[5m])) / 
    (sum(rate(fiml_cache_hits_total[5m])) + sum(rate(fiml_cache_misses_total[5m])))) > 50
  for: 5m
  labels:
    severity: warning
```

### Slow Requests
```yaml
- alert: SlowRequests
  expr: histogram_quantile(0.95, rate(fiml_request_duration_seconds_bucket[5m])) > 2
  for: 5m
  labels:
    severity: warning
```

### Unhealthy Watchdogs
```yaml
- alert: UnhealthyWatchdogs
  expr: fiml_watchdog_unhealthy_count > 0
  for: 1m
  labels:
    severity: critical
```

## Troubleshooting

### No Metrics in Grafana
```bash
# Check Prometheus targets
curl http://localhost:9091/api/v1/targets | jq

# Check FIML metrics endpoint
curl http://localhost:8000/metrics

# Verify Grafana datasource
curl -u admin:admin http://localhost:3000/api/datasources
```

### Dashboard Not Loading
```bash
# Check Grafana logs
docker-compose logs grafana

# Verify dashboard files
ls -la config/grafana/dashboards/

# Restart Grafana
docker-compose restart grafana
```

### Metrics Collection Issues
```bash
# Check FIML server logs
docker-compose logs fiml-server | grep -i prometheus

# Verify Prometheus config
cat config/prometheus.yml

# Restart Prometheus
docker-compose restart prometheus
```

## File Structure

```
FIML/
├── config/
│   ├── prometheus.yml                    # Prometheus scrape config
│   └── grafana/
│       ├── dashboards/
│       │   ├── dashboards.yml           # Dashboard provisioning
│       │   ├── fiml-overview.json       # System overview
│       │   ├── fiml-cache-analytics.json
│       │   ├── fiml-session-analytics.json
│       │   ├── fiml-watchdog-health.json
│       │   └── fiml-api-metrics.json
│       └── datasources/
│           └── prometheus.yml           # Prometheus datasource
├── fiml/
│   ├── server.py                        # Metrics endpoints
│   ├── cache/analytics.py               # Cache metrics
│   ├── sessions/analytics.py            # Session metrics
│   ├── watchdog/health.py               # Watchdog metrics
│   └── monitoring/
│       ├── performance.py               # Performance metrics
│       └── task_registry.py             # Task metrics
└── docs/
    └── monitoring/
        └── GRAFANA_INTEGRATION.md       # Full documentation
```

## Component Connections

```
FIML Components → Prometheus Metrics → Prometheus → Grafana Dashboards
                     ↓
                JSON Endpoints → Direct API Access
```

## Performance Impact

- CPU overhead: < 1%
- Memory overhead: ~50MB
- Network bandwidth: ~1KB/s
- Scrape interval: 15s (configurable)

## Security Notes

1. Change Grafana admin password
2. Secure /metrics endpoints in production
3. Use HTTPS for Grafana/Prometheus
4. Restrict network access
5. No PII in metrics

## Next Steps

1. ✅ Start services with `docker-compose up -d`
2. ✅ Access Grafana at http://localhost:3000
3. ✅ Verify dashboards are loaded
4. ✅ Check Prometheus targets are UP
5. ✅ Configure alerts (optional)
6. ✅ Set up Slack notifications (optional)

## Resources

- Full Documentation: `docs/monitoring/GRAFANA_INTEGRATION.md`
- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- FIML Deployment: `DEPLOYMENT.md`
