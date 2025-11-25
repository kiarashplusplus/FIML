# FIML AI Coding Agent Instructions

FIML (Financial Intelligence Meta-Layer) is an AI-native financial data MCP server with intelligent provider orchestration. This guide helps AI agents navigate the codebase effectively.

## Architecture Overview

**Core Philosophy**: FIML is a data arbitration layer that intelligently routes financial data requests across 16+ providers, with L1 (Redis)/L2 (PostgreSQL) caching, Ray-based multi-agent orchestration, and MCP protocol compliance.

### Key Components & Data Flow

```
Client (ChatGPT/Claude) → MCP API (fiml/server.py) → Arbitration Engine (fiml/arbitration/engine.py) 
→ Provider Registry (fiml/providers/) → Cache Manager (fiml/cache/manager.py) → L1 (Redis) / L2 (PostgreSQL)
```

**Agent Orchestration**: Ray-based workers in `fiml/agents/workers.py` (8 specialized agents decorated with `@ray.remote`) coordinate via `fiml/agents/orchestrator.py`

**FK-DSL Parser**: Lark-based grammar in `fiml/dsl/parser.py` (797 lines) - queries like `EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC)`

## Critical Development Workflows

### Running Tests
```bash
# Fast core tests (64 tests, ~10s) - run this before commits
make test

# Component-specific tests (CI mirrors this structure)
pytest tests/test_core.py -v              # Core models & exceptions
pytest tests/test_arbitration.py -v       # Provider scoring/fallback
pytest tests/test_providers.py -v         # Individual providers
pytest tests/test_agent_workflows.py -v   # Agent orchestration

# Full suite (439 passing, 25 skipped)
pytest -v -m "not live"

# Live system tests (requires Docker services)
pytest tests/test_live_system.py -v -m live
```

**Important**: Tests use autouse fixtures to mock external APIs (yfinance, ccxt, Azure OpenAI). See `tests/conftest.py` for comprehensive mocking strategy.

### Development Environment
```bash
make dev          # Install dev dependencies
make up           # Start Docker services (Redis, Postgres, Kafka, Ray)
make format       # Black + isort + ruff
make lint         # ruff + mypy
./quickstart.sh   # Interactive setup wizard
```

## Project-Specific Conventions

### Type Safety & Pydantic Models
- **All models use Pydantic v2** (`fiml/core/models.py`): `Asset`, `DataType`, `ProviderScore`, `ArbitrationPlan`
- **Field validation**: Use `@field_validator` decorators, not Pydantic v1 `@validator`
- **Enums**: Prefer `str, Enum` for serialization (e.g., `AssetType(str, Enum)`)

### Async/Await Everywhere
- **All I/O operations are async**: providers, cache, database, Ray workers
- **Pattern**: `async def fetch_*()` → `await provider.fetch_price(asset)`
- **Exception handling**: Wrap provider calls in try/except `ProviderError`, `ProviderTimeoutError`

### Provider Interface (`fiml/providers/base.py`)
Every provider implements `BaseProvider`:
```python
async def fetch_price(self, asset: Asset) -> ProviderResponse
async def fetch_ohlcv(self, asset: Asset, timeframe: str = "1d") -> ProviderResponse
async def supports_asset(self, asset: Asset) -> bool
async def get_health(self) -> ProviderHealth
```

**Adding a provider**: 
1. Inherit `BaseProvider` 
2. Register in `fiml/providers/registry.py` 
3. Add tests in `tests/providers/`
4. Mock external calls in `tests/conftest.py`

### Arbitration Engine 5-Factor Scoring
`fiml/arbitration/engine.py` scores providers on:
- **Freshness** (30%): Data age vs. `max_staleness_seconds`
- **Latency** (25%): P95 latency for user region
- **Uptime** (20%): Provider health score
- **Completeness** (15%): Required fields present
- **Reliability** (10%): Error rate history

**Execution**: Primary provider + 2 fallbacks, automatic retry on failure

### Cache Strategy (`fiml/cache/manager.py`)
- **L1 (Redis)**: 10-100ms target, 5-60min TTL based on market hours
- **L2 (PostgreSQL+TimescaleDB)**: 300-700ms, longer retention
- **Pattern**: Check L1 → L2 fallback → populate L1 on L2 hit
- **Keys**: `{asset.symbol}:{data_type}:{provider}` format
- **Metrics**: Hit rates, latencies tracked in `cache_analytics`

### Error Handling Pattern
```python
from fiml.core.exceptions import ProviderError, NoProviderAvailableError

try:
    data = await provider.fetch_price(asset)
except ProviderTimeoutError as e:
    logger.warning("Provider timeout", provider=provider.name, error=str(e))
    # Arbitration engine auto-falls back to next provider
except ProviderError as e:
    logger.error("Provider failed", provider=provider.name, error=str(e))
    raise ArbitrationError(f"All providers failed for {asset.symbol}")
```

### Logging (`fiml/core/logging.py`)
- **Structured logging with structlog**: `logger.info("message", key=value, asset=asset.symbol)`
- **Never use f-strings in log messages** - use key-value pairs for structured data
- **Levels**: DEBUG (development), INFO (important events), WARNING (recoverable), ERROR (failures)

## Integration Points & Dependencies

### MCP Protocol (`fiml/mcp/router.py`)
- **Tools**: `search-by-symbol`, `search-by-coin`, `execute-fk-dsl`, `analyze-narrative`
- **FastAPI router** at `/mcp/` endpoints
- **Tool registry**: Auto-discovery via `app.add_api_route()`

### WebSocket Streaming (`fiml/websocket/router.py`)
- **Endpoints**: `/ws/prices/{symbols}`, `/ws/stream`
- **Real-time updates**: Price + OHLCV data with configurable intervals
- **Max 50 concurrent symbols**, heartbeat every 30s

### Ray Multi-Agent System (`fiml/agents/`)
- **Workers**: `@ray.remote` decorated classes (7 agents in `workers.py`)
- **Orchestrator**: `AgentOrchestrator` coordinates tasks, manages Ray cluster
- **Workflows**: `deep_equity_analysis()`, `crypto_sentiment_analysis()` in `workflows.py`
- **Important**: Initialize Ray with `await agent_orchestrator.initialize()` before use

### Azure OpenAI Narratives (`fiml/narrative/`)
- **Generator**: `NarrativeGenerator` transforms structured data → natural language
- **Prompts**: Template library in `prompts.py` with expertise levels (beginner/intermediate/expert)
- **Quality validation**: `NarrativeValidator` checks readability, compliance, structure
- **Testing**: Mock Azure endpoint via `mock_azure_openai_httpx` fixture

## Testing Philosophy

### Fixture Strategy (`tests/conftest.py`)
- **Autouse fixtures mock all external APIs**: yfinance (`mock_yfinance_network_calls`), ccxt (`mock_ccxt_network_calls`), aiohttp (`mock_aiohttp_for_providers`)
- **Database fixtures**: `docker_services` starts Redis+Postgres, `init_session_db` creates tables
- **Singleton resets**: `reset_cache_singletons` prevents test pollution
- **Live tests**: Use `@pytest.mark.live` to skip mocks (requires `--run-live` flag)

### Component-Based CI (`docs/development/CI_WORKFLOW_STRUCTURE.md`)
- **9 specialized workflows**: Core, providers, arbitration, DSL, MCP, agents, infrastructure, integration, bot
- **Main CI** (`ci.yml`): Only core+cache tests (64 tests, fast feedback)
- **Badges**: Each component has independent status badge

### Coverage Expectations
- **Core components**: 97%+ (`fiml/core/`, `fiml/cache/`)
- **Providers**: 73% average (mocking complexity)
- **Overall**: 67% (439 passing tests, 100% success rate on core)

## Common Gotchas

1. **Datetime usage**: Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` (238 deprecation warnings to fix)
2. **Provider registry**: Call `await provider_registry.initialize()` before use (see `fiml/server.py` lifespan)
3. **Cache TTL**: Market hours matter - TTL adjusts dynamically (shorter during trading hours)
4. **Asset symbols**: Always uppercased via validator (`Asset.symbol.upper()`)
5. **Pydantic v2**: Use `model_dump()` not `.dict()`, `model_validate()` not `.parse_obj()`
6. **Ray workers**: Don't serialize heavy objects - pass asset symbols/IDs, fetch data in worker
7. **FK-DSL tokens**: Lark parser is case-sensitive; use uppercase keywords (`EVALUATE`, `COMPARE`)

## Key Files to Reference

- `fiml/core/models.py` - All Pydantic models (Asset, DataType enums, responses)
- `fiml/arbitration/engine.py` - Provider scoring/selection logic (422 lines)
- `fiml/providers/base.py` - Provider interface contract (137 lines)
- `fiml/cache/manager.py` - L1/L2 cache coordination (511 lines)
- `fiml/agents/workflows.py` - Production agent workflows (946 lines)
- `tests/conftest.py` - Comprehensive test fixtures and mocking strategy
- `Makefile` - All development commands
- `pyproject.toml` - Dependencies, tool configs (pytest, ruff, black)

## Documentation

- **Live docs**: https://kiarashplusplus.github.io/FIML/ (MkDocs)
- **Technical evaluation**: `docs/development/TECHNICAL_STRATEGIC_EVALUATION.md` (21KB deep dive)
- **Phase roadmap**: `README.md` (Phase 1 complete, Phase 2 60% done)
- **CI structure**: `docs/development/CI_WORKFLOW_STRUCTURE.md`
- **Contributing**: `CONTRIBUTING.md` (code style, PR process)

## Quick Reference Commands

```bash
# Development
./quickstart.sh                    # First-time setup
make dev && make up                # Start dev environment
make test                          # Fast core tests
pytest tests/test_*.py -v -k test_name  # Specific test

# Code Quality
make format                        # Auto-format (black/isort/ruff)
make lint                          # Type check (mypy + ruff)
ruff check fiml/ --fix             # Auto-fix linting issues

# Docker Services
make up                            # Start all services
make logs                          # View logs
make shell                         # Enter container shell
make psql / redis-cli              # Database clients

# Performance
make benchmark                     # Run benchmarks
make test-load-headless            # Load test (100 users, 5min)
pytest tests/performance/ -v       # Performance suite
```

When in doubt, check existing implementations in `fiml/providers/` or `fiml/agents/` for patterns, and `tests/` for testing strategies.
