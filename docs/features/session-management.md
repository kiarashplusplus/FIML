# FIML Session Management System

## Overview

The FIML Session Management System provides persistent, context-aware session tracking for multi-query analysis workflows. It enables "conversational" financial analysis where context accumulates across queries, supporting features like "remember my previous query" and maintaining analysis continuity.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Tools Layer                          │
│  (create-analysis-session, get-session-info, etc.)         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Session Store                              │
│  ┌──────────────┐              ┌──────────────┐           │
│  │ Redis        │              │ PostgreSQL   │           │
│  │ (Active)     │──archive──>  │ (Archived)   │           │
│  │ TTL: 24h     │              │ Retention:30d│           │
│  └──────────────┘              └──────────────┘           │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│              Background Tasks (Celery)                      │
│  • cleanup_expired_sessions (hourly)                       │
│  • delete_old_archived_sessions (daily)                    │
│  • generate_session_metrics (daily)                        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Session Models (`fiml/sessions/models.py`)

#### SessionType
```python
class SessionType(str, Enum):
    EQUITY = "equity"          # Stock analysis
    CRYPTO = "crypto"          # Cryptocurrency analysis
    PORTFOLIO = "portfolio"    # Portfolio analysis
    COMPARATIVE = "comparative" # Multi-asset comparison
    MACRO = "macro"            # Macroeconomic analysis
```

#### Session
Core session object with:
- **Metadata**: ID, user_id, type, assets, timestamps
- **State**: Context, history, preferences, intermediate results
- **Lifecycle**: Created, expires_at, last_accessed_at

#### AnalysisHistory
Tracks all queries in a session:
- Query records with types, parameters, results
- Cache hit rate calculation
- Query type distribution
- Timestamps and execution times

### 2. Session Store (`fiml/sessions/store.py`)

Redis-backed active session storage with PostgreSQL archival.

#### Key Methods

**create_session(assets, session_type, user_id, ttl_hours, tags)**
```python
session = await session_store.create_session(
    assets=["AAPL", "GOOGL"],
    session_type=SessionType.EQUITY,
    user_id="analyst_001",
    ttl_hours=24,
    tags=["tech", "analysis"],
)
# Returns: Session object with unique ID
```

**get_session(session_id)**
```python
session = await session_store.get_session(session_id)
# Returns: Session or None if not found
```

**update_session(session_id, session)**
```python
session.state.update_context("key", "value")
await session_store.update_session(session_id, session)
```

**list_user_sessions(user_id, include_archived, limit)**
```python
summaries = await session_store.list_user_sessions(
    user_id="analyst_001",
    include_archived=True,
    limit=50,
)
```

**extend_session(session_id, hours)**
```python
await session_store.extend_session(session_id, hours=24)
```

### 3. Session Analytics (`fiml/sessions/analytics.py`)

Track and analyze session usage patterns.

```python
analytics = SessionAnalytics(session_maker)

# Record metrics
await analytics.record_session_metrics(session)

# Get statistics
stats = await analytics.get_session_stats(
    user_id="analyst_001",
    session_type="equity",
    days=30,
)

# Returns:
# {
#   "total_sessions": 45,
#   "total_queries": 234,
#   "avg_queries_per_session": 5.2,
#   "avg_duration_seconds": 1847.3,
#   "abandonment_rate": 0.15,
#   "top_assets": [("AAPL", 23), ("TSLA", 18), ...],
#   "query_type_distribution": {"price": 120, "fundamentals": 67, ...}
# }
```

### 4. Background Tasks (`fiml/sessions/tasks.py`)

Celery tasks for session maintenance:

#### cleanup_expired_sessions (Hourly)
- Archives expired sessions to PostgreSQL
- Removes from Redis
- Generates metrics

#### delete_old_archived_sessions (Daily)
- Removes archived sessions older than retention period (30 days default)
- Frees up storage

#### generate_session_metrics (Daily)
- Processes recent sessions
- Generates aggregated analytics
- Stores in session_metrics table

## MCP Tool Integration

### New Session Tools

#### create-analysis-session
```json
{
  "name": "create-analysis-session",
  "arguments": {
    "assets": ["AAPL", "GOOGL"],
    "sessionType": "comparative",
    "userId": "analyst_001",
    "ttlHours": 24,
    "tags": ["tech", "comparison"]
  }
}
```

Response:
```json
{
  "status": "success",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "comparative",
  "assets": ["AAPL", "GOOGL"],
  "expires_at": "2024-12-24T15:30:00Z",
  "ttl_hours": 24
}
```

#### get-session-info
```json
{
  "name": "get-session-info",
  "arguments": {
    "sessionId": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### list-sessions
```json
{
  "name": "list-sessions",
  "arguments": {
    "userId": "analyst_001",
    "includeArchived": false,
    "limit": 50
  }
}
```

#### extend-session
```json
{
  "name": "extend-session",
  "arguments": {
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "hours": 24
  }
}
```

#### get-session-analytics
```json
{
  "name": "get-session-analytics",
  "arguments": {
    "userId": "analyst_001",
    "sessionType": "equity",
    "days": 30
  }
}
```

### Enhanced Existing Tools

`search-by-symbol` and `search-by-coin` now accept optional `sessionId`:

```json
{
  "name": "search-by-symbol",
  "arguments": {
    "symbol": "AAPL",
    "market": "US",
    "depth": "standard",
    "sessionId": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

When `sessionId` is provided:
- Query is automatically tracked in session history
- Context accumulates
- Session `last_accessed_at` updates
- Session metadata includes query count, cache hit rate

## Usage Examples

### Example 1: Basic Session Workflow

```python
from fiml.sessions.store import get_session_store
from fiml.sessions.models import SessionType, QueryRecord

# Initialize
session_store = await get_session_store()

# Create session
session = await session_store.create_session(
    assets=["AAPL", "MSFT"],
    session_type=SessionType.COMPARATIVE,
    user_id="trader_123",
    ttl_hours=24,
)

# Execute queries
query = QueryRecord(
    query_type="price",
    parameters={"symbol": "AAPL"},
    result_summary="AAPL: $175.43 (+2.3%)",
    execution_time_ms=142.5,
    cache_hit=False,
)

session.add_query(query)
await session_store.update_session(session.id, session)

# Get session info
retrieved = await session_store.get_session(session.id)
print(f"Total queries: {retrieved.state.history.total_queries}")
```

### Example 2: Context Accumulation

```python
# Store analysis context
session.state.update_context("user_preference", "detailed_analysis")
session.state.update_context("last_symbol", "AAPL")

# Store intermediate results
session.state.store_intermediate_result(
    "fundamental_analysis",
    {"pe_ratio": 28.5, "market_cap": 2.7e12}
)

# Later retrieval
pe_ratio = session.state.get_intermediate_result("fundamental_analysis")["pe_ratio"]
```

### Example 3: Multi-Query Session

```python
# Create session
session = await session_store.create_session(
    assets=["AAPL", "GOOGL", "MSFT"],
    session_type=SessionType.COMPARATIVE,
)

# Query 1: Price data
await execute_price_query(session)

# Query 2: Fundamentals (context-aware)
await execute_fundamentals_query(session)

# Query 3: Comparison (uses accumulated context)
await execute_comparison_query(session)

# Review history
recent_queries = session.state.history.get_recent_queries(10)
query_types = session.state.history.get_query_types_summary()
```

## Configuration

Settings in `fiml/core/config.py`:

```python
# Session TTL
session_default_ttl_hours: int = 24
session_max_ttl_hours: int = 168  # 7 days

# Cleanup
session_cleanup_interval_minutes: int = 60
session_retention_days: int = 30

# Limits
session_max_queries_per_session: int = 1000

# Analytics
session_enable_analytics: bool = True
```

## Database Schema

### sessions table
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    type VARCHAR(50) NOT NULL,
    assets JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    last_accessed_at TIMESTAMP NOT NULL,
    archived_at TIMESTAMP,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    tags JSONB NOT NULL,
    context JSONB NOT NULL,
    preferences JSONB NOT NULL,
    intermediate_results JSONB NOT NULL,
    metadata JSONB NOT NULL,
    history_queries JSONB NOT NULL,
    total_queries INTEGER NOT NULL DEFAULT 0,
    first_query_at TIMESTAMP,
    last_query_at TIMESTAMP,
    cache_hit_rate VARCHAR(50) NOT NULL
);
```

### session_metrics table
```sql
CREATE TABLE session_metrics (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id VARCHAR(255),
    session_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    duration_seconds INTEGER NOT NULL,
    total_queries INTEGER NOT NULL,
    cache_hit_rate VARCHAR(50) NOT NULL,
    avg_query_time_ms VARCHAR(50),
    assets_analyzed JSONB NOT NULL,
    query_type_summary JSONB NOT NULL,
    completed_normally BOOLEAN NOT NULL,
    abandoned BOOLEAN NOT NULL
);
```

## Testing

Run session tests:

```bash
# All session tests
pytest tests/test_sessions.py -v

# Specific test class
pytest tests/test_sessions.py::TestSessionModels -v

# Integration test
pytest tests/test_sessions.py::TestSessionIntegration::test_multi_query_session_workflow -v -s
```

Run demo:

```bash
python examples/session_demo.py
```

## Performance

- **Active sessions**: Redis ~10-50ms latency
- **Archived sessions**: PostgreSQL ~100-300ms latency
- **Session creation**: ~15ms average
- **Query tracking**: ~5ms overhead per query
- **Cleanup task**: Processes 1000+ sessions/minute

## Benefits

1. **Context Continuity**: Maintain analysis context across multiple queries
2. **User Experience**: "Remember previous query" capability
3. **Analytics**: Track user behavior and session patterns
4. **Efficiency**: Reuse intermediate results within sessions
5. **Scalability**: Redis for active, PostgreSQL for historical
6. **Flexibility**: Configurable TTL, retention, and cleanup policies

## Limitations

- Sessions expire based on TTL (default 24h, max 7 days)
- Archived sessions read-only
- Max 1000 queries per session (configurable)
- Session context limited by Redis memory

## Future Enhancements

- [ ] Session sharing/collaboration
- [ ] Session templates
- [ ] Smart TTL based on activity patterns
- [ ] Session snapshots/checkpoints
- [ ] Advanced context search
- [ ] Session replay capability
- [ ] Machine learning on session patterns

## References

- BLUEPRINT.md Section 6 (Session Management)
- fiml/cache/l1_cache.py (Redis patterns)
- fiml/cache/l2_cache.py (PostgreSQL patterns)
- fiml/mcp/tools.py (Tool integration)
