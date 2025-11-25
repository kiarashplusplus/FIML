# FIML Grafana Metrics & Analytics Integration

Complete integration guide for connecting all FIML metrics and analytics to Grafana for comprehensive system monitoring and observability.

## Overview

FIML now exposes comprehensive metrics from all major components through Prometheus and provides pre-built Grafana dashboards for visualization and monitoring.

### Components Integrated

1. **Cache Analytics** - L1/L2 cache performance metrics
2. **Session Analytics** - User session tracking and patterns
3. **Watchdog Health** - Real-time monitoring system health
4. **Performance Monitoring** - Request/response metrics
5. **Task Registry** - Async task completion tracking
6. **Provider Metrics** - External API provider performance
7. **Narrative Generation** - DSL and narrative metrics

## Architecture

```
┌─────────────────┐
│  FIML Server    │
│                 │
│  ┌───────────┐  │
│  │ Cache     │──┼──► Prometheus Metrics
│  │ Analytics │  │    (fiml_cache_*)
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │ Session   │──┼──► Prometheus Metrics
│  │ Analytics │  │    (fiml_session_*)
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │ Watchdog  │──┼──► Prometheus Metrics
│  │ Health    │  │    (fiml_watchdog_*)
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │Performance│──┼──► Prometheus Metrics
│  │ Monitor   │  │    (fiml_request_*, etc)
│  └───────────┘  │
│                 │
│     /metrics    │
└────────┬────────┘
         │
         ▼
   ┌──────────┐
   │Prometheus│◄──── Scrapes every 15s
   │  :9090   │
   └────┬─────┘
        │
        ▼
   ┌──────────┐
   │ Grafana  │◄──── Pre-built Dashboards
   │  :3000   │
   └──────────┘
```

## Available Dashboards

### 1. FIML System Overview
**UID:** `fiml-overview`  
**Purpose:** High-level system health and performance

**Panels:**
- Active requests & sessions
- Overall cache hit rate
- Healthy watchdogs count
- Task completion rate
- Request rate by status
- Request latency (p50, p95, p99)
- Provider request rates
- Provider latency

**Use Cases:**
- Quick system health check
- Performance at-a-glance
- Identifying system-wide issues

### 2. FIML Cache Analytics
**UID:** `fiml-cache-analytics`  
**Purpose:** Detailed cache performance monitoring

**Panels:**
- Overall cache hit rate gauge
- Hit rate by data type (timeseries)
- Cache latency percentiles (p50, p95, p99)
- Cache evictions rate by reason
- Cache size by level (L1/L2)
- Cache operations rate (hits/misses)

**Metrics:**
- `fiml_cache_hits_total`
- `fiml_cache_misses_total`
- `fiml_cache_latency_seconds`
- `fiml_cache_evictions_total`
- `fiml_cache_size_bytes`

**Use Cases:**
- Optimizing cache TTL settings
- Identifying cache pollution
- Monitoring cache effectiveness
- Capacity planning

### 3. FIML Session Analytics
**UID:** `fiml-session-analytics`  
**Purpose:** User session tracking and analysis

**Panels:**
- Active sessions count
- Sessions created (24h)
- Average session duration
- Average queries per session
- Session completion rate
- Session creation rate by type
- Session duration distribution
- Query rate by type

**Metrics:**
- `fiml_sessions_active_total`
- `fiml_sessions_created_total`
- `fiml_sessions_abandoned_total`
- `fiml_session_duration_seconds`
- `fiml_session_queries_total`

**Use Cases:**
- Understanding user behavior
- Identifying abandonment patterns
- Session optimization
- Feature usage analysis

### 4. FIML Watchdog Health
**UID:** `fiml-watchdog-health`  
**Purpose:** Real-time monitoring system health

**Panels:**
- Total/healthy/unhealthy watchdogs
- Overall success rate
- Watchdog check rate
- Events detected by watchdog
- Events by severity (critical/high/medium/low)
- Average check duration
- Check failures rate

**Metrics:**
- `fiml_watchdog_total_count`
- `fiml_watchdog_healthy_count`
- `fiml_watchdog_unhealthy_count`
- `fiml_watchdog_checks_total`
- `fiml_watchdog_events_detected_total`
- `fiml_watchdog_check_duration_seconds`
- `fiml_watchdog_check_failures_total`

**Use Cases:**
- System reliability monitoring
- Alert debugging
- Watchdog performance tuning
- Incident detection

### 5. FIML API Metrics
**UID:** `fiml-api-metrics`  
**Purpose:** Request/response performance

**Panels:**
- Request rate
- Request duration (p95)
- Active requests
- Provider request rate
- Provider latency (p95)

**Metrics:**
- `fiml_requests_total`
- `fiml_request_duration_seconds`
- `fiml_active_requests`
- `fiml_provider_requests_total`
- `fiml_provider_latency_seconds`

## Prometheus Metrics Reference

### Cache Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fiml_cache_hits_total` | Counter | `data_type`, `cache_level` | Total cache hits |
| `fiml_cache_misses_total` | Counter | `data_type`, `cache_level` | Total cache misses |
| `fiml_cache_latency_seconds` | Histogram | `data_type`, `cache_level`, `operation` | Cache operation latency |
| `fiml_cache_hit_rate` | Gauge | `data_type` | Cache hit rate percentage |
| `fiml_cache_size_bytes` | Gauge | `cache_level` | Cache size in bytes |
| `fiml_cache_evictions_total` | Counter | `cache_level`, `reason` | Total cache evictions |

### Session Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fiml_sessions_created_total` | Counter | `session_type` | Total sessions created |
| `fiml_sessions_active_total` | Gauge | - | Number of active sessions |
| `fiml_sessions_abandoned_total` | Counter | `session_type` | Total abandoned sessions |
| `fiml_session_duration_seconds` | Histogram | `session_type` | Session duration |
| `fiml_session_queries_total` | Histogram | `query_type` | Queries per session |

### Watchdog Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fiml_watchdog_total_count` | Gauge | - | Total registered watchdogs |
| `fiml_watchdog_healthy_count` | Gauge | - | Number of healthy watchdogs |
| `fiml_watchdog_unhealthy_count` | Gauge | - | Number of unhealthy watchdogs |
| `fiml_watchdog_checks_total` | Counter | `watchdog_name` | Total checks performed |
| `fiml_watchdog_check_failures_total` | Counter | `watchdog_name` | Total check failures |
| `fiml_watchdog_events_detected_total` | Counter | `watchdog_name`, `severity` | Events detected |
| `fiml_watchdog_check_duration_seconds` | Histogram | `watchdog_name` | Check duration |
| `fiml_watchdog_success_rate` | Gauge | - | Overall success rate |

### Performance Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fiml_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests |
| `fiml_request_duration_seconds` | Histogram | `method`, `endpoint` | Request duration |
| `fiml_active_requests` | Gauge | - | Active requests count |
| `fiml_slow_queries_total` | Counter | `operation` | Slow queries (>1s) |
| `fiml_task_completion_rate` | Gauge | - | Task completion rate |

### Provider Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fiml_provider_requests_total` | Counter | `provider`, `operation`, `status` | Provider API requests |
| `fiml_provider_latency_seconds` | Histogram | `provider`, `operation` | Provider API latency |

### Narrative Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fiml_narrative_generation_seconds` | Histogram | `style` | Narrative generation time |
| `fiml_dsl_execution_seconds` | Histogram | `query_type` | DSL query execution time |

## API Endpoints

### Prometheus Metrics
- **Endpoint:** `/metrics`
- **Format:** Prometheus exposition format
- **Update:** Real-time

### Custom JSON Metrics

#### Cache Metrics
```bash
GET /api/metrics/cache
```
Returns comprehensive cache analytics report including:
- Overall statistics
- Data type breakdown
- Cache pollution detection
- Hourly trends
- Optimization recommendations

#### Watchdog Metrics
```bash
GET /api/metrics/watchdog
```
Returns watchdog health summary including:
- Total/healthy/unhealthy counts
- Check statistics
- Event severity breakdown
- Detection rates

#### Performance Metrics
```bash
GET /api/metrics/performance
```
Returns performance monitoring data including:
- Cache metrics summary
- Slow queries
- Operation statistics
- Task metrics

#### Task Metrics
```bash
GET /api/metrics/tasks
```
Returns task registry statistics:
- Total active tasks
- Tasks by type
- Tasks by status

## Setup & Configuration

### 1. Start Services

```bash
docker-compose up -d
```

This starts:
- FIML Server (port 8000)
- Prometheus (port 9091)
- Grafana (port 3000)
- Supporting services (Redis, PostgreSQL, etc.)

### 2. Access Grafana

1. Open browser to `http://localhost:3000`
2. Login with default credentials:
   - Username: `admin`
   - Password: `admin`
3. Change password when prompted

### 3. Verify Data Source

1. Navigate to **Configuration** → **Data Sources**
2. Verify "Prometheus" is configured and healthy
3. URL should be: `http://prometheus:9090`

### 4. Access Dashboards

Pre-provisioned dashboards are automatically loaded:

1. Navigate to **Dashboards** → **Browse**
2. Look for folder: **FIML**
3. Available dashboards:
   - FIML System Overview
   - FIML Cache Analytics
   - FIML Session Analytics
   - FIML Watchdog Health
   - FIML API Metrics

### 5. Verify Metrics Collection

Check Prometheus is scraping metrics:

1. Open `http://localhost:9091/targets`
2. Verify all targets are "UP":
   - fiml-server
   - fiml-api-metrics (if configured)
   - postgres (if postgres-exporter running)
   - redis (if redis-exporter running)

## Customization

### Adding Custom Dashboards

1. Create JSON dashboard file in `config/grafana/dashboards/`
2. Follow existing dashboard structure
3. Restart Grafana: `docker-compose restart grafana`

### Modifying Scrape Intervals

Edit `config/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'fiml-server'
    scrape_interval: 15s  # Change as needed
    static_configs:
      - targets: ['fiml-server:8000']
```

### Adding Alert Rules

Create `config/prometheus/alerts/fiml-alerts.yml`:

```yaml
groups:
  - name: fiml_alerts
    rules:
      - alert: HighCacheMissRate
        expr: |
          100 * (
            sum(rate(fiml_cache_misses_total[5m])) / 
            (sum(rate(fiml_cache_hits_total[5m])) + sum(rate(fiml_cache_misses_total[5m])))
          ) > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High cache miss rate"
          description: "Cache miss rate is {{ $value }}%"
```

## Monitoring Best Practices

### 1. Set Up Alerts

Configure alerts for:
- Cache hit rate < 70%
- Request latency p95 > 2s
- Watchdog unhealthy count > 0
- Task completion rate < 80%
- High slow query count

### 2. Regular Reviews

- **Daily:** Check overview dashboard for anomalies
- **Weekly:** Review cache analytics for optimization opportunities
- **Monthly:** Analyze session patterns for product insights

### 3. Capacity Planning

Monitor trends for:
- Cache size growth
- Request rate increases
- Session duration patterns
- Provider latency changes

### 4. Performance Optimization

Use metrics to:
- Identify slow endpoints
- Optimize cache TTL settings
- Tune watchdog check intervals
- Scale workers based on load

## Troubleshooting

### Metrics Not Appearing

1. **Check FIML server logs:**
   ```bash
   docker-compose logs fiml-server | grep -i prometheus
   ```

2. **Verify /metrics endpoint:**
   ```bash
   curl http://localhost:8000/metrics
   ```

3. **Check Prometheus targets:**
   - Open `http://localhost:9091/targets`
   - Ensure "fiml-server" target is UP

### Dashboard Not Loading

1. **Verify dashboard files exist:**
   ```bash
   ls -la config/grafana/dashboards/
   ```

2. **Check Grafana logs:**
   ```bash
   docker-compose logs grafana
   ```

3. **Restart Grafana:**
   ```bash
   docker-compose restart grafana
   ```

### Missing Data Points

1. **Check scrape interval** - Data may be delayed
2. **Verify metric labels** - Ensure labels match dashboard queries
3. **Check time range** - Adjust dashboard time picker

### High Memory Usage

If Prometheus uses too much memory:

1. Reduce retention period in `prometheus.yml`:
   ```yaml
   storage:
     tsdb:
       retention.time: 7d  # Reduce from default 15d
   ```

2. Increase scrape intervals for less critical metrics

## Advanced Features

### PromQL Examples

**Cache hit rate by data type:**
```promql
100 * rate(fiml_cache_hits_total[5m]) / 
  (rate(fiml_cache_hits_total[5m]) + rate(fiml_cache_misses_total[5m]))
```

**Request rate by endpoint:**
```promql
sum(rate(fiml_requests_total[5m])) by (endpoint, status)
```

**Average session duration:**
```promql
avg(fiml_session_duration_seconds)
```

**Watchdog success rate:**
```promql
sum(fiml_watchdog_checks_total) / 
  (sum(fiml_watchdog_checks_total) + sum(fiml_watchdog_check_failures_total))
```

### Grafana Variables

Add dashboard variables for dynamic filtering:

```json
{
  "templating": {
    "list": [
      {
        "name": "data_type",
        "type": "query",
        "datasource": "Prometheus",
        "query": "label_values(fiml_cache_hits_total, data_type)"
      }
    ]
  }
}
```

## Integration with Other Tools

### Alertmanager

Configure Prometheus to send alerts to Alertmanager:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Slack Notifications

Configure Alertmanager to send to Slack:

```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_WEBHOOK_URL'
        channel: '#alerts'
```

### Export Dashboards

1. Open dashboard in Grafana
2. Click **Share** → **Export**
3. Save JSON for version control

## Performance Impact

Metrics collection has minimal performance impact:

- **CPU:** < 1% overhead
- **Memory:** ~50MB for Prometheus client
- **Network:** ~1KB/s for metrics export
- **Disk:** Metrics stored in Prometheus (not FIML)

## Security Considerations

1. **Secure Grafana:**
   - Change default admin password
   - Enable HTTPS in production
   - Restrict access to metrics endpoints

2. **Prometheus Security:**
   - Use authentication for /metrics endpoint
   - Restrict Prometheus network access
   - Enable TLS for scraping

3. **Sensitive Data:**
   - Metrics do not contain PII
   - API keys not exposed
   - Use label filtering if needed

## Related Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [FIML Deployment Guide](DEPLOYMENT_GUIDE.md)
- [FIML Monitoring Documentation](../docs/architecture/monitoring.md)

## Support

For issues or questions:
- GitHub Issues: [FIML Repository](https://github.com/kiarashplusplus/FIML)
- Documentation: `/docs/`
- Logs: `docker-compose logs -f`
