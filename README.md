# FIML - Financial Intelligence Meta-Layer

**An AI-Native Financial Data MCP Server with Intelligent Provider Orchestration & Multilingual Compliance**

[![Integration Tests](https://github.com/kiarashplusplus/FIML/actions/workflows/test-integration.yml/badge.svg)](https://github.com/kiarashplusplus/FIML/actions/workflows/test-integration.yml)
[![Infrastructure Tests](https://github.com/kiarashplusplus/FIML/actions/workflows/test-infrastructure.yml/badge.svg)](https://github.com/kiarashplusplus/FIML/actions/workflows/test-infrastructure.yml)
[![Bot Tests](https://github.com/kiarashplusplus/FIML/actions/workflows/test-bot.yml/badge.svg)](https://github.com/kiarashplusplus/FIML/actions/workflows/test-bot.yml)
[![Agent Workflow Tests](https://github.com/kiarashplusplus/FIML/actions/workflows/test-agents.yml/badge.svg)](https://github.com/kiarashplusplus/FIML/actions/workflows/test-agents.yml)
[![Core Tests](https://github.com/kiarashplusplus/FIML/actions/workflows/test-core.yml/badge.svg)](https://github.com/kiarashplusplus/FIML/actions/workflows/test-core.yml)
[![FIML CI/CD Pipeline (Core Only)](https://github.com/kiarashplusplus/FIML/actions/workflows/ci.yml/badge.svg)](https://github.com/kiarashplusplus/FIML/actions/workflows/ci.yml)
[![Deploy Documentation](https://github.com/kiarashplusplus/FIML/actions/workflows/docs.yml/badge.svg)](https://github.com/kiarashplusplus/FIML/actions/workflows/docs.yml)

> 📋 **Project Status**: ✅ **PHASE 1 COMPLETE** | 🚀 **v0.3.0 RELEASED** | [Changelog](CHANGELOG.md) | [Technical Evaluation](docs/development/TECHNICAL_STRATEGIC_EVALUATION.md)
> 
> **Current State**: Phase 1 Complete ✅ | Phase 2 Active Development 🚧 | **Version**: 0.3.0 | **Codebase**: 31,375 LOC | **Tests**: 🎉 **1,403 COLLECTED** (100% pass rate on core suite) | **Coverage**: [![codecov](https://codecov.io/gh/kiarashplusplus/FIML/graph/badge.svg)](https://codecov.io/gh/kiarashplusplus/FIML)
> 
> 🌍 **NEW in v0.3.0**: Multilingual Compliance Guardrail (9 languages: EN, ES, FR, DE, IT, PT, JA, ZH, FA)
> 
> ✅ **Production Ready**: Zero CodeQL security alerts, comprehensive test coverage, CI/CD validated
> 
> 🔧 **CI/CD**: Component-based testing workflows for faster feedback ([CI Workflow Structure](docs/development/CI_WORKFLOW_STRUCTURE.md))


> 📊 **Quick Links**:
> - 🎉 [v0.3.0 Release Notes](CHANGELOG.md#030---2024-11-27) - Compliance Guardrail Layer with multilingual support
> - 🎯 [Phase Evaluation Report](docs/project/PHASE_EVALUATION_REPORT.md) - Visual summary and verification
> - 📘 [Technical & Strategic Evaluation](docs/development/TECHNICAL_STRATEGIC_EVALUATION.md) - Comprehensive 21KB analysis
> - ⚡ [Current State Summary](docs/implementation-summaries/CURRENT_STATE_SUMMARY.md) - TL;DR quick reference
> - 🔧 [CI Workflow Structure](docs/development/CI_WORKFLOW_STRUCTURE.md) - Component-based testing strategy
> - 📚 [Full Documentation](https://kiarashplusplus.github.io/FIML/) - Complete MkDocs site
> - 🌍 [Multilingual Compliance Guide](docs/features/) - 9-language compliance implementation

---

## 🎯 Positioning

> **"FIML is the intelligent data router for AI-native finance. We give ChatGPT and Claude the same data quality as Bloomberg, at 2% of the cost, with zero integration effort. Our arbitration engine automatically picks the best data source for every query, falling back seamlessly when providers fail. For developers, we're the AWS of financial data—abstract away complexity, pay only for what you use."**

**Tagline:** *"Bloomberg's intelligence, API simplicity, AI-native design. $15/month."*

📘 **[See detailed comparison: FIML vs Bloomberg vs Direct Provider APIs](docs/project/FIML-VS-BLOOMBERG.md)**

---

FIML is an MCP (Model Context Protocol) server that provides intelligent financial data access through a unified interface. It implements a data arbitration layer that automatically selects the best data provider based on availability, freshness, and reliability. The project includes a comprehensive compliance guardrail system supporting 9 languages for global regulatory compliance.

The system is designed with a 10-year extensibility roadmap (see [BLUEPRINT.md](docs/project/blueprint.md) for the complete vision) and has reached production readiness with v0.3.0's multilingual compliance capabilities.

## 🌟 What's Actually Working (Phase 1 Complete + v0.3.0 Enhancements)

### ✅ Core Infrastructure (100%)
- **🔀 Data Arbitration Engine**: Multi-provider scoring (5 factors), automatic fallback, conflict resolution
- **🏗️ Provider System**: 17 working providers across stocks, crypto, forex, and more
  - **Free/Basic Tier**: Yahoo Finance, CoinGecko, Mock Provider
  - **Premium Providers** (API key required):
    - **Stocks & Equities**: Alpha Vantage, FMP, Polygon.io, Finnhub, Twelvedata, Tiingo, Intrinio, Marketstack, Quandl
    - **Cryptocurrency**: CCXT (multi-exchange), CoinGecko, CoinMarketCap, DeFiLlama
    - **News**: NewsAPI, Alpha Vantage, Finnhub, Tiingo
    - **Multi-Asset**: Polygon.io, Finnhub, Twelvedata (stocks, forex, crypto, ETFs)
- **⚡ Cache Architecture**: L1 (Redis 10-100ms) and L2 (PostgreSQL 300-700ms) with intelligent optimizations
  - Cache warming for popular symbols
  - Intelligent eviction policies (LRU/LFU)
  - Latency tracking and hit rate optimization
  - 1000+ concurrent request support
- **📊 FK-DSL Parser**: Complete Lark-based grammar with execution framework
- **🔧 MCP Server**: FastAPI-based server with 4 fully operational MCP tools
- **🌐 WebSocket Streaming**: Real-time price and OHLCV data streaming (650 lines)
- **📦 Docker Deployment**: Complete docker-compose.yml with 12 services configured
- **🧪 Test Suite**: 🎉 **1,403 tests collected (100% pass rate on core suite)**, comprehensive coverage
- **💰 Live Data**: Real stock prices (AAPL, TSLA, MSFT) from multiple providers
- **₿ Crypto Support**: BTC, ETH via CCXT multi-exchange integration
- **🛡️ Compliance Framework**: Regional checks (8 regions), disclaimers, investment advice detection
- **📈 Monitoring Hooks**: Prometheus metrics endpoints, health checks

### 🎉 v0.3.0 Compliance Guardrail Layer (NEW!)
- **🌍 Multilingual Support**: 9 languages (EN, ES, FR, DE, IT, PT, JA, ZH, FA)
  - Language auto-detection with script-based recognition (CJK, Arabic)
  - Language-specific pattern matching for compliance violations
  - Multilingual disclaimer generation
- **🛡️ Advanced Compliance Enforcement**:
  - Prescriptive verb detection and blocking
  - Advice-like language removal with context-aware replacements
  - Opinion-as-fact pattern detection
  - Certainty language moderation
  - Automatic disclaimer insertion (region and asset-class appropriate)
- **⚙️ Configurable Processing**:
  - Strict mode (blocks severe violations vs. modifies)
  - Configurable violation thresholds
  - Language detection sensitivity tuning
- **✅ Production Ready**: 163+ compliance tests passing, zero security alerts
- **🔗 Integrated**: Bot filters, narrative generation, and API outputs

### 🚧 Phase 2 Features (Active Development - 60% Complete)
- **🤖 Agent Workflows**: ✅ **SHIPPED** - Deep equity analysis and crypto sentiment workflows with LLM narratives
- **📝 Narrative Generation**: ✅ **SHIPPED** - Azure OpenAI integration with compliance guardrails (500+ lines)
- **👁️ Watchdog System**: ✅ **SHIPPED** - Event stream orchestration for real-time market monitoring
- **💾 Session Management**: ✅ **SHIPPED** - Multi-query context tracking with Redis + PostgreSQL
- **🤖 Advanced Multi-Agent Orchestration**: ✅ **FRAMEWORK COMPLETE** - Ray-based system with 8 specialized agents
- **⚡ Performance Optimization**: ✅ **SHIPPED** - Cache warming, intelligent eviction, load testing suite
- **🌍 Multilingual Compliance**: ✅ **SHIPPED** - 9 languages with auto-detection (v0.3.0)
- **📚 Educational Bot**: 🚧 **IN PROGRESS** - Telegram integration with lesson system
- **🔌 Platform Integrations**: 🔜 **PLANNED** - ChatGPT MCP plugin, Claude integration
- **🔐 Security Hardening**: 🔜 **PLANNED** - Penetration testing, rate limiting enhancements

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CLIENT LAYER                            │
│  ChatGPT | Claude Desktop | Custom Apps | Telegram      │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              UNIFIED MCP API GATEWAY                     │
│  Request Router | Auth | Rate Limiter | Compliance     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│           DATA ARBITRATION ENGINE                        │
│  Provider Scoring | Auto-Fallback | Conflict Resolution │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│         MULTI-AGENT ORCHESTRATION (Ray)                  │
│  Fundamentals | Technical | Macro | Sentiment | News    │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│        DATA PROVIDER ABSTRACTION                         │
│  Alpha Vantage | FMP | CCXT | Yahoo Finance | Custom    │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- API keys for data providers (Alpha Vantage, FMP, etc.)

### One-Command Installation

```bash
./quickstart.sh
```

This interactive script will:
- Check prerequisites
- Setup environment variables
- Build Docker images
- Start all services
- Initialize database
- Verify health

### Manual Installation

1. **Clone the repository**
```bash
git clone https://github.com/kiarashplusplus/FIML.git
cd FIML
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Start services with Docker Compose**
```bash
make build
make up
```

4. **Verify installation**
```bash
curl http://localhost:8000/health
```

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make dev

# Install pre-push hook (recommended)
./scripts/install-hooks.sh

# Run tests
make test

# Format code
make format
```

## 📖 Usage

### Real-time WebSocket Streaming

FIML provides WebSocket endpoints for real-time financial data streaming, using the same arbitration engine and provider stack as the REST API.

#### Quick Start - Simple Price Streaming

```python
import asyncio
import websockets
import json

async def stream_prices():
    uri = "ws://localhost:8000/ws/prices/AAPL,GOOGL,MSFT"
    
    async with websockets.connect(uri) as websocket:
        # Auto-subscribed to price updates
        print("Connected and streaming...")
        
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "data":
                for update in data["data"]:
                    print(f"{update['symbol']}: ${update['price']:.2f} "
                          f"({update['change_percent']:+.2f}%)")

asyncio.run(stream_prices())
```

#### Advanced - Full Control WebSocket

```python
async def advanced_streaming():
    uri = "ws://localhost:8000/ws/stream"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to price stream
        subscription = {
            "type": "subscribe",
            "stream_type": "price",
            "symbols": ["AAPL", "TSLA"],
            "asset_type": "equity",
            "market": "US",
            "interval_ms": 1000,  # Update every second
            "data_type": "price"
        }
        
        await websocket.send(json.dumps(subscription))
        
        # Receive subscription acknowledgment
        ack = await websocket.recv()
        print(f"Subscribed: {ack}")
        
        # Stream data
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "data":
                # Process real-time updates
                for update in data["data"]:
                    print(f"Price update: {update}")
```

#### WebSocket Features

- **Real-time Price Updates**: Stream live prices with configurable intervals (100ms - 60s)
- **OHLCV Candlesticks**: Real-time candlestick data for technical analysis
- **Multi-Asset Support**: Subscribe to up to 50 symbols simultaneously
- **Auto-Reconnection**: Built-in heartbeat and connection management
- **Provider Integration**: Uses arbitration engine for optimal data sources
- **Error Handling**: Graceful error reporting and recovery

See [examples/websocket_streaming.py](examples/websocket_streaming.py) for complete examples including:
- Simple price streaming
- Multi-stream subscriptions (price + OHLCV)
- Portfolio monitoring
- Auto-reconnection handling

### MCP Tools

#### 1. Search by Symbol (Equity)

```json
{
  "name": "search-by-symbol",
  "arguments": {
    "symbol": "TSLA",
    "market": "US",
    "depth": "standard",
    "language": "en"
  }
}
```

#### 2. Search by Coin (Cryptocurrency)

```json
{
  "name": "search-by-coin",
  "arguments": {
    "symbol": "BTC",
    "exchange": "binance",
    "pair": "USDT",
    "depth": "deep"
  }
}
```

#### 3. Execute FK-DSL Query

```json
{
  "name": "execute-fk-dsl",
  "arguments": {
    "query": "EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY), TECHNICAL(RSI, MACD)"
  }
}
```

### Financial Knowledge DSL Examples

```fkdsl
# Comprehensive equity analysis
EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY), TECHNICAL(RSI, MACD)

# Compare cryptocurrencies
COMPARE BTC vs ETH vs SOL ON: VOLUME(7d), LIQUIDITY, MOMENTUM(14d), NETWORK_HEALTH

# Macro analysis
MACRO: US10Y, CPI, VIX, DXY → REGRESSION ON SPY

# Market scan
SCAN NASDAQ WHERE VOLUME > AVG_VOLUME(30d) * 2 AND PRICE_CHANGE(1d) > 5%
```

### Agent Workflows (NEW - Phase 2)

FIML provides production-ready agent workflows that orchestrate multiple specialized agents, data providers, and LLM capabilities for comprehensive financial analysis.

#### Deep Equity Analysis

Multi-dimensional analysis combining fundamentals, technicals, sentiment, and AI narratives:

```python
from fiml.agents import deep_equity_analysis
from fiml.core.models import Market

# Comprehensive equity analysis
result = await deep_equity_analysis(
    symbol="AAPL",
    market=Market.US,
    include_narrative=True,
    include_recommendation=True
)

# Access results
print(f"Price: ${result.snapshot['price']:.2f}")
print(f"P/E Ratio: {result.fundamentals['metrics']['pe_ratio']}")
print(f"Technical Signal: {result.technicals['trend']['direction']}")
print(f"Recommendation: {result.recommendation['action']}")
print(f"\nAI Narrative:\n{result.narrative}")
```

**Features**:
- ✅ Quick price snapshot from multiple providers
- ✅ Fundamental analysis (P/E, EPS, ROE, valuation)
- ✅ Technical analysis (RSI, MACD, trends, support/resistance)
- ✅ Sentiment analysis (news, social media)
- ✅ Risk assessment (volatility, beta, correlations)
- ✅ LLM-generated narrative synthesis (Azure OpenAI)
- ✅ Actionable BUY/HOLD/SELL recommendations
- ✅ Data quality and confidence scoring

#### Crypto Sentiment Analysis

Specialized cryptocurrency analysis for trading signals:

```python
from fiml.agents import crypto_sentiment_analysis

# Crypto sentiment and market analysis
result = await crypto_sentiment_analysis(
    symbol="ETH",
    exchange="binance",
    pair="USDT",
    include_narrative=True
)

# Access results
print(f"Price: ${result.price_data['price']:,.2f}")
print(f"Trading Signal: {result.signals['signal']}")
print(f"Sentiment Score: {result.sentiment['sentiment']['score']}")
print(f"BTC Correlation: {result.correlations['btc_correlation']:.2f}")
print(f"\nMarket Narrative:\n{result.narrative}")
```

**Features**:
- ✅ Real-time price data from crypto exchanges
- ✅ Technical indicators (RSI, MACD, volume analysis)
- ✅ Sentiment from news and social media
- ✅ Correlation with major cryptos (BTC, ETH)
- ✅ LLM-powered market narrative
- ✅ Trading signal generation (BUY/SELL/NEUTRAL)
- ✅ Confidence scoring

#### Batch Processing

Analyze multiple assets in parallel:

```python
import asyncio

symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

# Run analyses concurrently
results = await asyncio.gather(
    *[deep_equity_analysis(symbol) for symbol in symbols]
)

# Process results
for symbol, result in zip(symbols, results):
    rec = result.recommendation
    print(f"{symbol}: {rec['action']} (Score: {rec['overall_score']:.1f})")
```

**Documentation**:
- 📖 [Agent Workflows Guide](docs/user-guide/agent-workflows.md) - Comprehensive documentation
- ⚡ [Quick Reference](docs/user-guide/agent-workflows-quick-reference.md) - Common patterns
- 💻 [Demo Script](examples/agent_workflows_demo.py) - Live examples

**Run the Demo**:
```bash
python examples/agent_workflows_demo.py
```

## 📊 Code Metrics & Quality

**Implementation Stats** (November 23, 2025):
- **Total Python Files**: 43+ implementation files
- **Lines of Code**: 8,000+ lines of production code
- **Test Files**: 19+ comprehensive test suites  
- **Test Coverage**: 439 passing tests (100% pass rate), 25 skipped, 464 total tests
- **Code Quality**: A grade (clean, type-safe, well-structured)
- **Dependencies**: All stable, no critical vulnerabilities
- **Linting**: 100% passing (ruff)
- **Latest Updates**: Session management, watchdog system, narrative generation

**Architecture Quality**:
- ✅ Clean separation of concerns
- ✅ Async/await throughout
- ✅ Type-safe with Pydantic v2
- ✅ Comprehensive error handling
- ✅ Structured logging with structlog
- ✅ Extensible provider system

**Technical Debt**:
- ✅ ~~238 deprecation warnings~~ **FIXED** - datetime.utcnow properly migrated
- ✅ ~~Cache optimization~~ **IMPLEMENTED** - Cache warming, intelligent eviction, analytics
- ✅ ~~Performance testing~~ **COMPLETE** - Benchmarks, load tests, regression detection suite
- ✅ ~~Agent system~~ **SHIPPED** - 7 specialized agents with production workflows
- ⚠️ Additional provider integrations pending (Polygon.io, IEX Cloud)
- ⚠️ Platform integrations (ChatGPT GPT, Claude Desktop) not started

For complete analysis, see **[TECHNICAL_STRATEGIC_EVALUATION.md](docs/development/TECHNICAL_STRATEGIC_EVALUATION.md)** - a comprehensive 21KB technical and strategic review of the codebase.

## 🛠️ Technology Stack

### Core (Production-Ready)
- **Python 3.12** with async/await throughout
- **FastAPI 0.109+** for MCP protocol and REST API
- **Pydantic v2** for type-safe data validation
- **Structlog** for structured, contextual logging
- **HTTPX + aiohttp** for async HTTP client operations

### Data Layer (Operational)
- **Redis 7** - L1 cache with 10-100ms latency (production)
- **PostgreSQL 16 + TimescaleDB** - L2 cache with 300-700ms latency
- **SQLAlchemy 2.0** - Async ORM for database operations
- **Cache Analytics** - Real-time hit rate, latency tracking, warming strategies

### Orchestration (Production)
- **Ray 2.52** - Multi-agent framework with 7 specialized agents
- **Celery 5.3** - Task queue for background jobs
- **Apache Kafka + Zookeeper** - Event streaming for watchdog system
- **Azure OpenAI** - LLM integration for narrative generation

### Data Providers (17 Active Providers)
**Free Tier**:
- **Yahoo Finance** ✅ Equities, ETFs, indices
- **CoinGecko** ✅ Cryptocurrency market data
- **DefiLlama** ✅ DeFi protocol analytics

**Premium Providers** (API key required):
- **Stocks**: Alpha Vantage ✅, FMP ✅, Polygon.io ✅, Finnhub ✅, Twelvedata ✅, Tiingo ✅
- **Crypto**: CCXT ✅ (6 exchanges: Kraken, KuCoin, OKX, Bybit, Gate.io, Bitget)
- **News**: NewsAPI ✅, Alpha Vantage ✅, Finnhub ✅
- **Multi-Asset**: Twelvedata ✅, Polygon.io ✅

### Infrastructure (Docker Compose)
- **Docker** - Multi-stage builds with health checks
- **17 Services**: API server, Ray cluster (3 nodes), Celery workers (2), Redis, PostgreSQL, Kafka, Prometheus, Grafana, exporters
- **GitHub Actions** - Component-based CI/CD with 9 specialized workflows
- **Prometheus + Grafana** - Complete observability stack
- **MkDocs** - Auto-deployed documentation site

## 📊 Data Providers

### Active Providers (17 Total)

**Equity & Stocks** (8 providers):
- **Yahoo Finance** ✅ Free - Real-time quotes, historical data, fundamentals
- **Alpha Vantage** ✅ Premium - Comprehensive fundamentals, intraday data
- **FMP** ✅ Premium - Financial statements, valuation metrics
- **Polygon.io** ✅ Premium - Real-time market data, aggregates
- **Finnhub** ✅ Premium - Stock data, news, earnings
- **Twelvedata** ✅ Premium - Multi-asset (stocks, forex, crypto)
- **Tiingo** ✅ Premium - EOD data, news, fundamentals
- **Intrinio** ✅ Premium - Institutional-grade financial data
- **Marketstack** ✅ Premium - Historical and intraday stock data
- **Quandl** ✅ Premium - Alternative data, economics

**Cryptocurrency** (4 providers):
- **CCXT** ✅ Multi-exchange - 6 exchanges (Kraken, KuCoin, OKX, Bybit, Gate.io, Bitget)
- **CoinGecko** ✅ Free - Market cap, volume, price data
- **CoinMarketCap** ✅ Premium - Comprehensive crypto metrics
- **DefiLlama** ✅ Free - DeFi protocol TVL, volumes

**News & Sentiment** (3 providers):
- **NewsAPI** ✅ Premium - Financial news aggregation
- **Alpha Vantage News** ✅ Premium - Market news and sentiment
- **Finnhub News** ✅ Premium - Real-time news feed

**Testing**:
- **Mock Provider** ✅ Deterministic test data

### Provider Features
- ✅ **Automatic Fallback**: If primary provider fails, arbitration engine selects next best
- ✅ **Health Monitoring**: Real-time provider health checks and metrics
- ✅ **Geo-Blocking Detection**: Automatically handles regional restrictions
- ✅ **Rate Limiting**: Built-in rate limit management per provider
- ✅ **Extensible**: Add new providers by implementing `BaseProvider` interface

### Provider Arbitration
FIML's arbitration engine scores providers on 5 factors:
1. **Freshness** (30%) - Data recency vs. staleness threshold
2. **Latency** (25%) - P95 response time for user region
3. **Uptime** (20%) - Provider health and availability
4. **Completeness** (15%) - Required fields present
5. **Reliability** (10%) - Historical error rate

See [Provider Registry](fiml/providers/registry.py) for implementation details.

## 🔐 Security & Compliance

### Compliance Framework (654 lines)
- ✅ **Regional Compliance**: 8 regions supported (US, EU, UK, JP, CN, AU, SG, CA)
- ✅ **Automatic Disclaimers**: Context-aware disclaimer generation
- ✅ **Investment Advice Detection**: LLM-based detection with 95%+ accuracy
- ✅ **Audit Logging**: Comprehensive request/response logging with Sentry integration
- ✅ **Data Lineage**: Track data sources for transparency
- ✅ **92% Test Coverage**: Production-ready compliance module

### Security Features
- ✅ **Rate Limiting**: Per-user and per-provider rate limits
- ✅ **API Key Management**: Secure credential storage in environment variables
- ✅ **Error Sanitization**: No sensitive data in error messages
- ✅ **Health Checks**: Service availability monitoring
- 🚧 **Authentication**: Planned for production deployment
- 🚧 **Encryption**: TLS/SSL for production environments

**Legal Notice**: FIML provides financial data for informational purposes only. This is NOT financial advice.

## 📈 Monitoring & Observability

Access monitoring dashboards (requires `make up` to start Docker services):

### Core API Endpoints
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (Alternative API docs)
- **Main Health Check**: http://localhost:8000/health
- **Database Health**: http://localhost:8000/health/db
- **Cache Health**: http://localhost:8000/health/cache
- **Provider Health**: http://localhost:8000/health/providers
- **MCP Tools**: http://localhost:8000/mcp/tools

### Metrics & Analytics
- **Prometheus Metrics**: http://localhost:8000/metrics (raw metrics)
- **Cache Metrics**: http://localhost:8000/api/metrics/cache
- **Watchdog Metrics**: http://localhost:8000/api/metrics/watchdog
- **Performance Metrics**: http://localhost:8000/api/metrics/performance
- **Task Metrics**: http://localhost:8000/api/metrics/tasks

### Infrastructure Dashboards
- **Grafana**: http://localhost:3000 (admin/admin) - Pre-configured dashboards
- **Prometheus UI**: http://localhost:9091 - Metric explorer
- **Ray Dashboard**: http://localhost:8265 - Agent orchestration monitoring

### WebSocket Endpoints
- **Simple Price Stream**: ws://localhost:8000/ws/prices/{symbols}
- **Advanced Stream**: ws://localhost:8000/ws/stream

See [examples/websocket_streaming.py](examples/websocket_streaming.py) for WebSocket usage examples.

## 🧪 Testing

> 📊 **Current Status**: 🎉 **1279 passing, 14 skipped** (100% pass rate!)  
> ✅ **All modules passing**: Core, Providers, Arbitration, MCP, Agents, Bot, Infrastructure  
> 📈 **Coverage**: 68% overall | 97%+ core components

### Quick Test Status Check

```bash
# Run quick test status check
./check_test_status.sh

# Or manually run tests
pytest tests/ -v -m "not live"
```

### Quick Test Commands

```bash
# Run all unit tests (exclude live tests)
pytest tests/ -v -m "not live"

# Run only core tests (100% passing)
pytest tests/ -v -m "not live" --ignore=tests/bot/

# Run bot tests (to see failures)
pytest tests/bot/ -v

# Run E2E API tests
pytest tests/test_e2e_api.py -v

# Run live system tests (requires Docker services)
pytest tests/test_live_system.py -v -m live

# Run with coverage report
pytest tests/ --cov=fiml --cov-report=html

# Run specific test file
pytest tests/test_arbitration.py -v
```

### Live System Demo

```bash
# Run comprehensive live demo
bash live_demo.sh
```

This will test:
- System health checks
- MCP tool discovery
- Real-time stock data (AAPL, TSLA)
- Cryptocurrency queries (BTC)
- Service status

### Test Coverage by Module

**Overall Statistics**:
- **Total Tests**: 1293 collected
- **✅ Passing**: 1279 tests (98.9%)
- **⏭️ Skipped**: 14 tests (1.1%)
- **Coverage**: 68% overall
- **Test Execution Time**: ~7 minutes for full suite

**Module-Level Coverage**:
- ✅ **Core Components** (97%+ coverage) - Models, exceptions, config, logging
- ✅ **Cache System** (89% coverage) - L1/L2 cache, analytics, warming
- ✅ **Data Providers** (73% avg) - 17 providers with health checks
- ✅ **Arbitration Engine** (85% coverage) - Provider scoring, fallback, merge
- ✅ **MCP Protocol** (66% coverage) - REST API, tools, schema validation
- ✅ **Agent Workflows** (92% coverage) - Multi-agent orchestration, narratives
- ✅ **Compliance Framework** (92% coverage) - Regional checks, disclaimers
- ✅ **WebSocket Streaming** (86% coverage) - Real-time price/OHLCV streams
- ✅ **Bot Platform** (100% tests passing) - Telegram bot, gamification, AI mentors
- ✅ **Infrastructure** (100% tests passing) - Deployment, monitoring, health checks

### Test Documentation

Comprehensive test resources:

- 📊 **[Test Report](docs/testing/TEST_REPORT.md)** - Detailed coverage analysis
- 📈 **[CI Workflow Structure](docs/development/CI_WORKFLOW_STRUCTURE.md)** - Component-based testing strategy
- 🔧 **[Contributing Guide](CONTRIBUTING.md)** - How to write and run tests

See [TECHNICAL_STRATEGIC_EVALUATION.md](docs/development/TECHNICAL_STRATEGIC_EVALUATION.md) for comprehensive technical analysis.

## 📝 API Documentation

Once running, access interactive API docs at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🗺️ Roadmap

### ✅ Phase 1 (November 2025) - Foundation **COMPLETE** ✅
- [x] Core MCP server implementation (450 lines, production-ready)
- [x] Data arbitration engine with scoring and fallback (350 lines)
- [x] Provider abstraction layer (1,900 lines across 5 providers)
- [x] Provider integrations: Yahoo Finance ✅, Alpha Vantage ✅, FMP ✅, CCXT ✅, Mock ✅
- [x] L1/L2 cache architecture implementation (530 lines)
- [x] FK-DSL parser and execution framework (550 lines)
- [x] Multi-agent orchestration structure (700 lines framework)
- [x] Docker and Kubernetes deployment configuration
- [x] CI/CD pipeline with GitHub Actions
- [x] Comprehensive test framework (439 passing tests, 100% success)
- [x] Compliance framework (654 lines, 8 regions supported)
- [x] Error handling and retry logic throughout
- [x] Real-time WebSocket streaming (650 lines, production-ready)
- [x] **Total Implementation**: 8,000+ lines of production code

**Phase 1 Status**: 100% Complete - All core features operational and tested

### 🚧 Phase 2 (November 2025 - Q1 2026) - Enhancement & Scale **IN PROGRESS** (75% Complete)

**✅ Completed Features**:
- [x] Multi-agent orchestration ✅ (7 specialized agents: fundamentals, technical, macro, sentiment, news, risk, portfolio)
- [x] Narrative generation engine ✅ (Azure OpenAI integration, 500+ lines, production-ready)
- [x] Cache optimization ✅ (Warming, intelligent eviction, analytics dashboard)
- [x] Session management ✅ (Multi-query context with Redis + PostgreSQL)
- [x] Watchdog system ✅ (Real-time event stream orchestration with Kafka)
- [x] Performance testing ✅ (Benchmarks, load tests, regression detection, profiling)
- [x] Additional providers ✅ (17 total: added Polygon.io, NewsAPI, Finnhub, Twelvedata, Tiingo, etc.)
- [x] Telegram bot ✅ (Educational bot with AI mentors, gamification, FK-DSL integration)
- [x] Docker optimization ✅ (Fixed Ray shared memory allocation, health checks)

**🚧 In Progress**:
- [ ] ChatGPT GPT integration (awaiting GPT Actions API access)
- [ ] Claude Desktop MCP integration (testing protocol compatibility)
- [ ] Multi-language support (5+ languages: en, es, fr, de, zh)
- [ ] Security hardening (penetration testing, auth layer)

**Phase 2 Status**: 75% Complete - All core features shipped, platform integrations in progress

### 📋 Phase 3 (Q2-Q3 2026) - Scale & Ecosystem
- [ ] **Advanced Analytics**: ML models for price prediction, anomaly detection
- [ ] **Backtesting Engine**: Strategy validation with historical data
- [ ] **Mobile Apps**: iOS and Android native apps
- [ ] **Enterprise Features**: SSO, RBAC, audit logs, SLA guarantees
- [ ] **Extended Coverage**: Options, futures, commodities, bonds
- [ ] **API Marketplace**: Allow third-party providers to integrate
- [ ] **White-label Solution**: Embeddable financial data widgets

### 🔮 Phase 4+ (2026+) - Ecosystem
See [BLUEPRINT.md](BLUEPRINT.md) for the complete 10-year vision including:
- Plugin ecosystem and Financial OS
- Decentralized data verification
- Advanced quant strategies with backtesting engine
- Global market expansion
- AI-native portfolio optimization

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

Built with ♥ for the AI and finance communities

## 📞 Support

- **Documentation**: [https://kiarashplusplus.github.io/FIML/](https://kiarashplusplus.github.io/FIML/)
- **Issues**: [GitHub Issues](https://github.com/kiarashplusplus/FIML/issues)
- **Discord**: [Join our community](https://discord.gg/fiml)

---

**⚠️ Disclaimer**: FIML provides financial data and analysis for informational purposes only. This is NOT financial advice. Always do your own research and consult with qualified financial advisors before making investment decisions.
