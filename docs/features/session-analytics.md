# Session Analytics Feature

## Overview

The session analytics feature provides comprehensive insights into user activity, session patterns, and platform usage. It tracks metrics across all user sessions and generates actionable analytics for understanding user behavior.

## Key Features

### 📊 Metrics Tracked

1. **Session Counts**
   - Total sessions (with metrics)
   - Active sessions (currently running)
   - Archived sessions (completed)

2. **Query Analytics**
   - Total queries across all sessions
   - Average queries per session
   - Query type distribution

3. **Duration Metrics**
   - Average session duration
   - Session lifecycle tracking

4. **Asset Analysis**
   - Most analyzed assets (top 10)
   - Asset occurrence counts

5. **Session Types**
   - Type distribution breakdown
   - Type-specific filtering

6. **Engagement Metrics**
   - Abandonment rate
   - Session completion patterns

7. **Tag Analytics**
   - Popular tags (top 10)
   - Tag usage frequency

## Usage

### MCP Tool: `get-session-analytics`

#### Basic Usage

```json
{
  "name": "get-session-analytics",
  "arguments": {
    "userId": "analyst_001",
    "days": 30
  }
}
```

#### With Filters

```json
{
  "name": "get-session-analytics",
  "arguments": {
    "userId": "analyst_001",
    "sessionType": "equity",
    "days": 7
  }
}
```

#### All Users (Platform-Wide)

```json
{
  "name": "get-session-analytics",
  "arguments": {
    "days": 30
  }
}
```

### Python API

```python
from fiml.sessions.analytics import SessionAnalytics
from fiml.sessions.store import get_session_store

# Initialize
session_store = await get_session_store()
analytics = SessionAnalytics(session_store._session_maker)

# Get user-specific analytics
stats = await analytics.get_session_stats(
    user_id="analyst_001",
    days=30
)

# Get session-type specific analytics
equity_stats = await analytics.get_session_stats(
    user_id="analyst_001",
    session_type="equity",
    days=7
)

# Platform-wide analytics
platform_stats = await analytics.get_session_stats(
    days=30
)
```

## Response Format

### For New Users (No History)

```json
{
  "status": "success",
  "total_sessions": 0,
  "active_sessions": 0,
  "archived_sessions": 0,
  "total_queries": 0,
  "avg_duration_seconds": 0.0,
  "avg_queries_per_session": 0.0,
  "abandonment_rate": 0.0,
  "period_days": 30,
  "user_id": "new_user",
  "session_type": null,
  "top_assets": [],
  "query_type_distribution": {},
  "session_type_breakdown": {},
  "popular_tags": [],
  "message": "No session metrics available yet. Create sessions to start tracking analytics."
}
```

### For Existing Users (With History)

```json
{
  "status": "success",
  "total_sessions": 45,
  "active_sessions": 3,
  "archived_sessions": 42,
  "total_queries": 234,
  "avg_duration_seconds": 1847.3,
  "avg_queries_per_session": 5.2,
  "abandonment_rate": 0.15,
  "period_days": 30,
  "user_id": "analyst_001",
  "session_type": null,
  "top_assets": [
    {"symbol": "AAPL", "count": 23},
    {"symbol": "TSLA", "count": 18},
    {"symbol": "MSFT", "count": 15}
  ],
  "query_type_distribution": {
    "price": 120,
    "fundamentals": 67,
    "technical": 47
  },
  "session_type_breakdown": {
    "equity": 28,
    "comparative": 12,
    "portfolio": 5
  },
  "popular_tags": [
    {"tag": "tech", "count": 15},
    {"tag": "growth", "count": 12},
    {"tag": "research", "count": 8}
  ]
}
```

## Metrics Explained

### total_sessions
Total number of sessions with recorded metrics in the specified time period. This count includes only sessions that have been archived and have metrics recorded.

### active_sessions
Number of currently active (non-expired) sessions. These are sessions that are still running and haven't reached their expiration time.

### archived_sessions
Number of sessions that have been archived within the specified time period. Sessions are typically archived when they expire or are explicitly closed.

### total_queries
Aggregate count of all queries executed across all sessions in the time period. Useful for understanding platform usage intensity.

### avg_duration_seconds
Average time a session stays active, calculated from session creation to expiration/archival. Measured in seconds.

### avg_queries_per_session
Average number of queries executed per session. Indicates session engagement level.

### abandonment_rate
Percentage of sessions that were abandoned (expired with fewer than 2 queries). High abandonment rates may indicate UX issues or unclear session purposes.

### top_assets
List of the 10 most frequently analyzed assets/symbols across all sessions, with occurrence counts. Useful for content recommendations and trend analysis.

### query_type_distribution
Breakdown of query types (e.g., "price", "fundamentals", "technical") with counts. Shows what types of analysis users are performing.

### session_type_breakdown
Distribution of sessions by type (equity, crypto, portfolio, comparative, macro). Indicates which analysis workflows are most popular.

### popular_tags
The 10 most commonly used tags across all sessions. Helps identify common themes and use cases.

## Use Cases

### 1. User Engagement Analysis
Track how actively users are engaging with the platform:

```python
stats = await analytics.get_session_stats(user_id="user_123", days=7)
engagement_score = stats["avg_queries_per_session"] * (1 - stats["abandonment_rate"])
```

### 2. Content Recommendations
Identify trending assets for content creation:

```python
stats = await analytics.get_session_stats(days=7)
trending_assets = stats["top_assets"][:5]  # Top 5 trending
```

### 3. Feature Usage Analysis
Understand which analysis types are most popular:

```python
stats = await analytics.get_session_stats(days=30)
most_used_queries = max(stats["query_type_distribution"].items(), key=lambda x: x[1])
```

### 4. User Segmentation
Segment users by activity level:

```python
# Get individual user stats
user_stats = await analytics.get_session_stats(user_id="user_123", days=30)

# Categorize
if user_stats["total_sessions"] > 20:
    segment = "power_user"
elif user_stats["total_sessions"] > 5:
    segment = "regular_user"
else:
    segment = "occasional_user"
```

### 5. Platform Health Monitoring
Monitor overall platform health:

```python
stats = await analytics.get_session_stats(days=1)
if stats["abandonment_rate"] > 0.3:
    # Alert: High abandonment rate
    send_alert("High session abandonment detected")
```

### 6. A/B Testing Analysis
Compare analytics across different user groups or time periods:

```python
# Week 1 (control)
week1_stats = await analytics.get_session_stats(days=7)

# Week 2 (after feature launch)
week2_stats = await analytics.get_session_stats(days=7)

improvement = (
    week2_stats["avg_queries_per_session"] - 
    week1_stats["avg_queries_per_session"]
)
```

## Best Practices

### 1. Regular Archival
Ensure sessions are archived regularly to generate metrics:

```python
# Archive expired sessions
await session_store.archive_expired_sessions()
```

### 2. Consistent Tagging
Use consistent tags for better categorization:

```python
session = await session_store.create_session(
    assets=["AAPL"],
    session_type=SessionType.EQUITY,
    tags=["tech", "research", "long-term"]  # Consistent tags
)
```

### 3. Record Metrics
Record metrics when sessions complete:

```python
from fiml.sessions.analytics import SessionAnalytics

analytics = SessionAnalytics(session_store._session_maker)
await analytics.record_session_metrics(session)
```

### 4. Time Period Selection
Choose appropriate time periods for analysis:

- **Daily**: `days=1` - Real-time monitoring
- **Weekly**: `days=7` - Short-term trends
- **Monthly**: `days=30` - Medium-term patterns
- **Quarterly**: `days=90` - Long-term trends

### 5. Filter Strategically
Use filters to focus on specific segments:

```python
# Equity-specific analytics
equity_stats = await analytics.get_session_stats(
    session_type="equity",
    days=30
)

# User-specific analytics
user_stats = await analytics.get_session_stats(
    user_id="analyst_001",
    days=30
)
```

## Integration Examples

### Dashboard Widget

```python
async def get_dashboard_metrics(user_id: str):
    """Get key metrics for dashboard display"""
    analytics = SessionAnalytics(session_store._session_maker)
    stats = await analytics.get_session_stats(user_id=user_id, days=7)
    
    return {
        "sessions_this_week": stats["total_sessions"],
        "active_now": stats["active_sessions"],
        "avg_session_time": f"{stats['avg_duration_seconds'] / 60:.1f} min",
        "engagement_rate": f"{(1 - stats['abandonment_rate']) * 100:.1f}%",
        "top_asset": stats["top_assets"][0]["symbol"] if stats["top_assets"] else "N/A"
    }
```

### Email Report

```python
async def generate_weekly_report(user_id: str):
    """Generate weekly analytics email report"""
    analytics = SessionAnalytics(session_store._session_maker)
    stats = await analytics.get_session_stats(user_id=user_id, days=7)
    
    report = f"""
    Weekly Activity Report
    =====================
    
    Sessions: {stats['total_sessions']} ({stats['active_sessions']} active)
    Total Queries: {stats['total_queries']}
    Avg Session Duration: {stats['avg_duration_seconds'] / 60:.1f} minutes
    
    Most Analyzed Assets:
    {'\n'.join(f"  - {a['symbol']} ({a['count']} times)" for a in stats['top_assets'][:5])}
    
    Session Types:
    {'\n'.join(f"  - {k}: {v}" for k, v in stats['session_type_breakdown'].items())}
    """
    
    return report
```

### Real-time Monitoring

```python
async def monitor_platform_health():
    """Monitor platform health in real-time"""
    analytics = SessionAnalytics(session_store._session_maker)
    
    # Last hour
    stats = await analytics.get_session_stats(days=1)
    
    alerts = []
    
    if stats["abandonment_rate"] > 0.4:
        alerts.append("High abandonment rate detected")
    
    if stats["total_sessions"] == 0:
        alerts.append("No sessions created recently")
    
    if stats["avg_queries_per_session"] < 2:
        alerts.append("Low engagement detected")
    
    return alerts
```

## Database Schema

The analytics feature uses two main tables:

### session_metrics
Stores aggregated metrics for archived sessions:

```sql
CREATE TABLE session_metrics (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id VARCHAR(255),
    session_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER NOT NULL,
    total_queries INTEGER NOT NULL DEFAULT 0,
    cache_hit_rate VARCHAR(50) NOT NULL DEFAULT '0.0',
    avg_query_time_ms VARCHAR(50),
    assets_analyzed JSONB NOT NULL DEFAULT '[]',
    query_type_summary JSONB NOT NULL DEFAULT '{}',
    completed_normally BOOLEAN NOT NULL DEFAULT FALSE,
    abandoned BOOLEAN NOT NULL DEFAULT FALSE
);
```

### sessions
Stores active and archived session records:

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    type VARCHAR(50) NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]',
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    -- ... other fields
);
```

## Performance Considerations

### Indexing
Key indexes for efficient queries:

```sql
CREATE INDEX idx_session_metrics_user_id ON session_metrics(user_id);
CREATE INDEX idx_session_metrics_created_at ON session_metrics(created_at);
CREATE INDEX idx_session_metrics_type ON session_metrics(session_type);
CREATE INDEX idx_sessions_archived ON sessions(is_archived);
```

### Query Optimization
- Use appropriate time periods to limit result sets
- Apply filters (user_id, session_type) to reduce data scanned
- Archive old sessions regularly to keep active dataset manageable

### Caching
Consider caching analytics results for frequently accessed queries:

```python
from fiml.cache import cache_manager

@cache_manager.cached(ttl=300)  # Cache for 5 minutes
async def get_cached_analytics(user_id: str, days: int):
    analytics = SessionAnalytics(session_store._session_maker)
    return await analytics.get_session_stats(user_id=user_id, days=days)
```

## Troubleshooting

### No metrics returned
**Symptom**: Analytics returns all zeros

**Solution**: 
1. Check if sessions have been archived
2. Verify metrics are being recorded on archival
3. Check the time period - may be too short

```python
# Force archive and record metrics
await session_store.archive_expired_sessions()
await analytics.record_session_metrics(session)
```

### Incorrect counts
**Symptom**: Session counts don't match expectations

**Solution**:
1. Check if filters are applied correctly
2. Verify time period boundaries
3. Ensure metrics table is in sync

### Performance issues
**Symptom**: Analytics queries are slow

**Solution**:
1. Add appropriate indexes
2. Reduce time period
3. Apply filters to limit data scanned
4. Consider caching frequent queries

## Future Enhancements

Planned improvements to the analytics feature:

1. **Time-series analytics** - Track trends over time
2. **Cohort analysis** - Compare user cohorts
3. **Retention metrics** - Track user retention
4. **Export formats** - CSV, Excel, PDF reports
5. **Real-time analytics** - WebSocket-based live updates
6. **Predictive analytics** - ML-based usage predictions
7. **Custom metrics** - User-defined analytics
8. **Benchmarking** - Compare against platform averages

## Related Documentation

- [Session Management](./session-management.md)
- [Session Quick Reference](../reference-guides/SESSION_QUICK_REFERENCE.md)
- [MCP Tools Test Results](../testing/MCP_TOOLS_TEST_RESULTS.md)
- [Session Implementation Summary](../implementation-summaries/SESSION_IMPLEMENTATION_SUMMARY.md)
