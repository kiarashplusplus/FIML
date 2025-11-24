# FIML Project Structure

```
FIML/
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI/CD pipeline
├── config/
│   ├── prometheus.yml             # Prometheus configuration
│   └── grafana/                   # Grafana dashboards
├── examples/
│   └── basic_usage.py             # Usage examples
├── fiml/
│   ├── __init__.py
│   ├── server.py                  # Main FastAPI server
│   ├── arbitration/               # Data Arbitration Engine
│   │   ├── __init__.py
│   │   └── engine.py              # Core arbitration logic
│   ├── core/                      # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py              # Settings and configuration
│   │   ├── exceptions.py          # Custom exceptions
│   │   ├── logging.py             # Structured logging
│   │   └── models.py              # Core domain models
│   ├── mcp/                       # MCP Protocol Implementation
│   │   ├── __init__.py
│   │   ├── router.py              # MCP API router
│   │   └── tools.py               # MCP tool implementations
│   ├── providers/                 # Data Provider Abstraction
│   │   ├── __init__.py
│   │   ├── base.py                # Base provider interface
│   │   ├── registry.py            # Provider registry
│   │   ├── mock_provider.py       # Mock provider for testing
│   │   ├── yahoo_finance.py       # Yahoo Finance provider
│   │   ├── alpha_vantage.py       # Alpha Vantage provider (TODO)
│   │   ├── fmp.py                 # FMP provider (TODO)
│   │   └── ccxt_provider.py       # CCXT crypto provider (TODO)
│   ├── cache/                     # Cache Layer (TODO)
│   │   ├── __init__.py
│   │   ├── l1_cache.py            # Redis L1 cache
│   │   └── l2_cache.py            # PostgreSQL L2 cache
│   ├── dsl/                       # FK-DSL Parser & Executor (TODO)
│   │   ├── __init__.py
│   │   ├── parser.py              # Lark-based DSL parser
│   │   └── executor.py            # DSL execution engine
│   ├── agents/                    # Multi-Agent Orchestration (TODO)
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Ray orchestrator
│   │   ├── fundamentals.py        # Fundamentals worker
│   │   ├── technical.py           # Technical analysis worker
│   │   ├── macro.py               # Macro economics worker
│   │   ├── sentiment.py           # Sentiment analysis worker
│   │   └── correlation.py         # Correlation worker
│   ├── compliance/                # Compliance Framework (TODO)
│   │   ├── __init__.py
│   │   ├── router.py              # Compliance routing
│   │   └── disclaimers.py         # Disclaimer generation
│   └── tasks/                     # Celery Tasks (TODO)
│       ├── __init__.py
│       └── celery.py              # Celery configuration
├── k8s/                           # Kubernetes manifests
│   └── deployment.yaml
├── scripts/
│   ├── init-db.sql                # Database initialization
│   └── dev-setup.sh               # Development setup script
├── tests/
│   ├── conftest.py                # Pytest configuration
│   ├── test_arbitration.py        # Arbitration engine tests
│   └── test_providers.py          # Provider tests
├── .dockerignore
├── .env.example                   # Example environment variables
├── .gitignore
├── BLUEPRINT.md                   # Comprehensive system blueprint
├── CONTRIBUTING.md                # Contribution guidelines
├── DEPLOYMENT.md                  # Deployment guide
├── docker-compose.yml             # Docker Compose configuration
├── Dockerfile                     # Multi-stage Dockerfile
├── LICENSE                        # Apache 2.0 License
├── Makefile                       # Development commands
├── pyproject.toml                 # Python project configuration
└── README.md                      # Project README
```

## Module Responsibilities

### Core (`fiml/core/`)
- Configuration management
- Domain models and types
- Logging infrastructure
- Custom exceptions

### MCP (`fiml/mcp/`)
- FastAPI routing for MCP protocol
- Tool implementations (search-by-symbol, search-by-coin, etc.)
- Request/response handling

### Providers (`fiml/providers/`)
- Abstract base provider interface
- Provider registry and lifecycle management
- Individual provider implementations
- Health monitoring

### Arbitration (`fiml/arbitration/`)
- Provider scoring algorithm
- Execution plan generation
- Auto-fallback logic
- Multi-provider data merging
- Conflict resolution

### Cache (TODO)
- L1 (Redis) in-memory cache
- L2 (PostgreSQL/TimescaleDB) persistent cache
- Predictive cache pre-warming
- TTL management

### DSL (TODO)
- FK-DSL grammar definition
- Lark-based parser
- Execution plan generation
- DAG scheduling

### Agents (TODO)
- Ray-based distributed orchestration
- Specialized worker agents
- Task routing and coordination
- Result aggregation

### Compliance (TODO)
- Regional restriction checks
- Disclaimer generation
- Audit logging
- Content filtering

## Key Design Patterns

1. **Provider Pattern**: Extensible provider interface for data sources
2. **Registry Pattern**: Centralized provider management
3. **Strategy Pattern**: Pluggable arbitration and merge strategies
4. **Factory Pattern**: Dynamic task and worker creation
5. **Observer Pattern**: Event streaming and notifications
6. **Repository Pattern**: Data access abstraction

## Development Workflow

1. **Feature Development**: Create feature branch from `develop`
2. **Testing**: Write tests, run `make test`
3. **Code Quality**: Run `make format` and `make lint`
4. **Documentation**: Update relevant docs
5. **PR**: Submit pull request for review
6. **CI/CD**: Automated testing and deployment
