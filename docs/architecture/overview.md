# Architecture Overview

FIML (Financial Intelligence Meta-Layer) is built with a modular, scalable architecture designed for high performance and extensibility.

## System Layers

### Client Layer
Supports multiple client types:
- ChatGPT plugins
- Claude Desktop integration
- Custom applications
- Telegram bots

### API Gateway
Unified MCP API with:
- Request routing
- Authentication
- Rate limiting
- Compliance checks

### Data Arbitration Engine
Intelligent provider selection based on:
- Availability (30%)
- Freshness (25%)
- Reliability (25%)
- Latency (15%)
- Cost (5%)

### Multi-Agent Framework
Ray-based distributed agents:
- Fundamentals analysis
- Technical analysis
- Macro analysis
- Sentiment analysis
- News aggregation

### Provider Layer
Multiple data sources:
- Yahoo Finance
- Alpha Vantage
- Financial Modeling Prep (FMP)
- CCXT (crypto exchanges)
- Custom providers

## Project Structure

```
FIML/
├── fiml/
│   ├── server.py                  # Main FastAPI server
│   ├── arbitration/               # Data Arbitration Engine
│   ├── core/                      # Core utilities (Config, Logging, Models)
│   ├── mcp/                       # MCP Protocol Implementation
│   ├── providers/                 # Data Provider Abstraction
│   ├── cache/                     # Cache Layer (Redis + Postgres)
│   ├── dsl/                       # FK-DSL Parser & Executor
│   ├── agents/                    # Multi-Agent Orchestration
│   └── compliance/                # Compliance Framework
├── config/                        # Configuration files (Prometheus, Grafana)
├── k8s/                           # Kubernetes manifests
├── scripts/                       # Helper scripts
└── tests/                         # Test suite
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

### Cache (`fiml/cache/`)
- L1 (Redis) in-memory cache
- L2 (PostgreSQL/TimescaleDB) persistent cache
- Predictive cache pre-warming

### Agents (`fiml/agents/`)
- Ray-based distributed orchestration
- Specialized worker agents
- Task routing and coordination

## Key Design Principles

1. **Provider Agnostic**: Easy to add new data sources
2. **Cache-First**: Multi-tier caching for performance
3. **Fault Tolerant**: Automatic fallback and retry
4. **Observable**: Comprehensive monitoring and logging
5. **Compliant**: Built-in regional compliance

## Security

Security features include:
- API key management and rotation
- Rate limiting and throttling
- Request authentication
- Compliance checks per region
- Audit logging

For more details on security and compliance, see the [Compliance Framework](../architecture/overview.md#security).
