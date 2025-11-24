# Session Management Quick Reference

## Quick Start

### 1. Setup Database
```bash
python scripts/setup_session_db.py create
```

### 2. Create Session (Python)
```python
from fiml.sessions.store import get_session_store
from fiml.sessions.models import SessionType

session_store = await get_session_store()

session = await session_store.create_session(
    assets=["AAPL", "GOOGL"],
    session_type=SessionType.EQUITY,
    user_id="user_123",
    ttl_hours=24,
)

session_id = session.id  # Save this!
```

### 3. Create Session (MCP Tool)
```json
{
  "name": "create-analysis-session",
  "arguments": {
    "assets": ["AAPL", "GOOGL"],
    "sessionType": "equity",
    "userId": "user_123",
    "ttlHours": 24
  }
}
```

### 4. Use Session in Queries (MCP)
```json
{
  "name": "search-by-symbol",
  "arguments": {
    "symbol": "AAPL",
    "sessionId": "YOUR_SESSION_ID"
  }
}
```

## Common Operations

### Track Query
```python
from fiml.sessions.models import QueryRecord

query = QueryRecord(
    query_type="price",
    parameters={"symbol": "AAPL"},
    result_summary="AAPL: $175.43 (+2.3%)",
)

session.add_query(query)
await session_store.update_session(session.id, session)
```

### Store Context
```python
session.state.update_context("user_preference", "detailed")
session.state.store_intermediate_result("analysis_1", {"data": "value"})
await session_store.update_session(session.id, session)
```

### Get Session Info
```python
session = await session_store.get_session(session_id)

print(f"Queries: {session.state.history.total_queries}")
print(f"Cache hit rate: {session.state.history.cache_hit_rate}")
print(f"Recent queries: {session.state.history.get_recent_queries(5)}")
```

### Extend Session
```python
await session_store.extend_session(session_id, hours=24)
```

### List User Sessions
```python
summaries = await session_store.list_user_sessions(
    user_id="user_123",
    include_archived=False,
    limit=50,
)
```

### Get Analytics
```python
from fiml.sessions.analytics import SessionAnalytics

analytics = SessionAnalytics(session_store._session_maker)
stats = await analytics.get_session_stats(
    user_id="user_123",
    days=30,
)
```

## MCP Tools Reference

### create-analysis-session
**Creates new session**
- `assets`: string[] (required)
- `sessionType`: "equity" | "crypto" | "portfolio" | "comparative" | "macro" (required)
- `userId`: string (optional)
- `ttlHours`: number (optional, default: 24)
- `tags`: string[] (optional)

### get-session-info
**Get session details**
- `sessionId`: string (required)

### list-sessions
**List user sessions**
- `userId`: string (required)
- `includeArchived`: boolean (optional, default: false)
- `limit`: number (optional, default: 50)

### extend-session
**Extend session TTL**
- `sessionId`: string (required)
- `hours`: number (optional, default: 24)

### get-session-analytics
**Get usage statistics**
- `userId`: string (optional)
- `sessionType`: string (optional)
- `days`: number (optional, default: 30)

## Session Types

- `equity` - Stock analysis
- `crypto` - Cryptocurrency analysis
- `portfolio` - Portfolio analysis
- `comparative` - Multi-asset comparison
- `macro` - Macroeconomic analysis

## Configuration

In `.env` or environment:

```bash
# Session TTL
SESSION_DEFAULT_TTL_HOURS=24
SESSION_MAX_TTL_HOURS=168

# Cleanup
SESSION_CLEANUP_INTERVAL_MINUTES=60
SESSION_RETENTION_DAYS=30

# Limits
SESSION_MAX_QUERIES_PER_SESSION=1000
SESSION_ENABLE_ANALYTICS=true
```

## Background Tasks

Configure in Celery beat:

```python
# Hourly cleanup
cleanup_expired_sessions

# Daily archival cleanup  
delete_old_archived_sessions

# Daily metrics
generate_session_metrics
```

## Testing

```bash
# All tests
pytest tests/test_sessions.py -v

# Integration test with output
pytest tests/test_sessions.py::TestSessionIntegration::test_multi_query_session_workflow -v -s

# Demo
python examples/session_demo.py
```

## Troubleshooting

### Sessions not persisting
- Check Redis connection: `redis-cli ping`
- Check PostgreSQL connection
- Verify `session_store.initialize()` called

### Sessions expiring too quickly
- Increase `session_default_ttl_hours`
- Use `extend_session()` to extend lifetime

### Cleanup not running
- Check Celery beat scheduler is running
- Check `session_cleanup_interval_minutes` setting
- View Celery logs for task execution

### Memory issues
- Reduce `session_max_queries_per_session`
- Decrease `session_default_ttl_hours`
- Increase cleanup frequency

## Best Practices

1. **Always provide session_id** when doing multi-query analysis
2. **Set appropriate TTL** based on workflow (hours for short, days for long)
3. **Tag sessions** for easy filtering and organization
4. **Store context** for complex analyses
5. **Use analytics** to optimize session patterns
6. **Clean up sessions** when done manually if needed
7. **Monitor metrics** for usage patterns

## Performance Tips

- Active sessions: Redis (10-50ms)
- Archived sessions: PostgreSQL (100-300ms)
- Query tracking: ~5ms overhead
- Batch operations when possible
- Use `list_user_sessions` with pagination

## Example Workflows

### Comparative Analysis
```python
# 1. Create session
session = await session_store.create_session(
    assets=["AAPL", "MSFT", "GOOGL"],
    session_type=SessionType.COMPARATIVE,
)

# 2. Query each asset
for symbol in ["AAPL", "MSFT", "GOOGL"]:
    # Execute query (automatically tracked if session_id provided)
    result = await search_by_symbol(symbol, session_id=str(session.id))
    
# 3. Compare results using accumulated context
session = await session_store.get_session(session.id)
all_results = session.state.intermediate_results
```

### Portfolio Analysis
```python
# 1. Create portfolio session
session = await session_store.create_session(
    assets=["SPY", "QQQ", "IWM"],
    session_type=SessionType.PORTFOLIO,
    tags=["etf", "diversified"],
)

# 2. Analyze each holding
# 3. Store allocation context
session.state.update_context("allocation", {
    "SPY": 0.6, "QQQ": 0.3, "IWM": 0.1
})

# 4. Track performance over time
```

## Documentation

- Full docs: `docs/SESSION_MANAGEMENT.md`
- Implementation summary: `SESSION_IMPLEMENTATION_SUMMARY.md`
- Code examples: `examples/session_demo.py`
- Tests: `tests/test_sessions.py`
