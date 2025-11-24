# FIML - Financial Intelligence Meta-Layer

**An AI-Native Financial Data MCP Server with Intelligent Provider Orchestration**

> 📋 **Project Status**: ✅ **PHASE 1 COMPLETE** | [Test Results](docs/testing/TEST_REPORT.md) [![FIML CI/CD Pipeline](https://github.com/kiarashplusplus/FIML/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kiarashplusplus/FIML/actions/workflows/ci.yml) | [Technical Evaluation](docs/development/TECHNICAL_STRATEGIC_EVALUATION.md)
> 
> **Current State**: Phase 1 Complete ✅ | Phase 2 In Development 🚧 | **Version**: 0.2.1 | **Tests**: 🎉 **100% PASSING** (439 passed, 25 skipped) | **Coverage**: [![codecov](https://codecov.io/gh/kiarashplusplus/FIML/graph/badge.svg)](https://codecov.io/gh/kiarashplusplus/FIML)
> 
> ✅ **Verified**: Tests pass identically with and without .env file (GitHub runner compatible)
> 
> 🔧 **CI/CD**: Component-based testing workflows for faster feedback ([CI Workflow Structure](docs/development/CI_WORKFLOW_STRUCTURE.md))


> 📊 **Quick Links**:
> - 🎯 [Phase Evaluation Report](docs/project/PHASE_EVALUATION_REPORT.md) - Visual summary and verification
> - 📘 [Technical & Strategic Evaluation](docs/development/TECHNICAL_STRATEGIC_EVALUATION.md) - Comprehensive 21KB analysis
> - ⚡ [Current State Summary](docs/implementation-summaries/CURRENT_STATE_SUMMARY.md) - TL;DR quick reference
> - 🔧 [CI Workflow Structure](docs/development/CI_WORKFLOW_STRUCTURE.md) - Component-based testing strategy
> - 📚 [Full Documentation](https://kiarashplusplus.github.io/FIML/) - Complete MkDocs site

---

## 🎯 Positioning

> **"FIML is the intelligent data router for AI-native finance. We give ChatGPT and Claude the same data quality as Bloomberg, at 2% of the cost, with zero integration effort. Our arbitration engine automatically picks the best data source for every query, falling back seamlessly when providers fail. For developers, we're the AWS of financial data—abstract away complexity, pay only for what you use."**

**Tagline:** *"Bloomberg's intelligence, API simplicity, AI-native design. $15/month."*

📘 **[See detailed comparison: FIML vs Bloomberg vs Direct Provider APIs](docs/project/FIML-VS-BLOOMBERG.md)**

---

FIML is an MCP (Model Context Protocol) server that provides intelligent financial data access through a unified interface. It implements a data arbitration layer that automatically selects the best data provider based on availability, freshness, and reliability. The project is designed with a 10-year extensibility roadmap (see [BLUEPRINT.md](docs/project/blueprint.md) for the complete vision).

## 🌟 What's Actually Working (Phase 1 Complete)

### ✅ Core Infrastructure (100%)
- **🔀 Data Arbitration Engine**: Multi-provider scoring (5 factors), automatic fallback, conflict resolution
- **🏗️ Provider System**: 16 working providers across stocks, crypto, forex, and more
  - **Free/Basic Tier**: Yahoo Finance, CoinGecko, Mock Provider
  - **Premium Providers** (API key required):
    - **Stocks & Equities**: Alpha Vantage, FMP, Polygon.io, Finnhub, Twelvedata, Tiingo, Intrinio, Marketstack, Quandl
    - **Cryptocurrency**: CCXT (multi-exchange), CoinGecko, CoinMarketCap
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
- **🧪 Test Suite**: 🎉 **439 passing tests (100% pass rate)**, 25 skipped, comprehensive coverage
- **💰 Live Data**: Real stock prices (AAPL, TSLA, MSFT) from multiple providers
- **₿ Crypto Support**: BTC, ETH via CCXT multi-exchange integration
- **🛡️ Compliance Framework**: Regional checks (8 regions), disclaimers, investment advice detection
- **📈 Monitoring Hooks**: Prometheus metrics endpoints, health checks

### 🚧 Phase 2 Features (In Development)
- **🤖 Agent Workflows**: ✅ **SHIPPED** - Deep equity analysis and crypto sentiment workflows with LLM narratives
- **📝 Narrative Generation**: ✅ **IMPLEMENTED** - Azure OpenAI integration for AI-powered market insights (500+ lines)
- **👁️ Watchdog System**: ✅ **IMPLEMENTED** - Event stream orchestration for real-time market monitoring
- **💾 Session Management**: ✅ **IMPLEMENTED** - Multi-query context tracking with Redis + PostgreSQL
- **🤖 Advanced Multi-Agent Orchestration**: ✅ **FRAMEWORK COMPLETE** - Ray-based system with 7 specialized agents
- **⚡ Performance Optimization**: ✅ **IMPLEMENTED** - Cache warming, intelligent eviction, load testing suite
- **🌍 Multi-language Support**: Not yet implemented - planned for Q2 2026
- **🔌 Platform Integrations**: ChatGPT, Claude, Telegram - not yet started
- **🔐 Security Hardening**: Penetration testing - pending

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
- ⚠️ 238 deprecation warnings (datetime.utcnow usage)
- ⚠️ Cache optimization needed
- ⚠️ Performance testing not yet done
- ⚠️ Agent system needs completion

For complete analysis, see **[TECHNICAL_STRATEGIC_EVALUATION.md](TECHNICAL_STRATEGIC_EVALUATION.md)** - a comprehensive 21KB technical and strategic review of the codebase.

## 🛠️ Technology Stack

### Core (Implemented)
- **Python 3.11+** with async/await throughout
- **FastAPI + Starlette** for MCP protocol support
- **Pydantic v2** for data validation and settings management
- **Structlog** for structured logging

### Data Layer (Ready)
- **Redis** - L1 cache layer (10-100ms target)
- **PostgreSQL + TimescaleDB** - L2 cache layer (300-700ms target)
- **SQLAlchemy** - Async ORM

### Orchestration (Configured)
- **Ray** - Distributed multi-agent framework
- **Celery** - Task queue (configured)
- **Apache Kafka** - Event streaming (configured)

### Data Providers (Current)
- **Yahoo Finance** ✅ Fully implemented
- **Mock Provider** ✅ For testing
- **Alpha Vantage** 🚧 Planned
- **FMP** 🚧 Planned  
- **CCXT** 🚧 Planned for crypto

### Infrastructure
- **Docker** - Multi-stage containerization
- **Kubernetes** - Production orchestration  
- **GitHub Actions** - CI/CD pipeline
- **Prometheus + Grafana** - Monitoring (configured)

## 📊 Data Providers

### Currently Implemented
- **Yahoo Finance** ✅ - Equities, ETFs, indices (free, reliable)
- **Alpha Vantage** ✅ - Premium equity data and fundamentals
- **FMP** ✅ - Financial Modeling Prep for financial statements
- **CCXT** ✅ - Multi-exchange cryptocurrency data (Binance, Coinbase, Kraken)
- **Mock Provider** ✅ - Testing and development

### Planned (Phase 2+)
- **Polygon.io** - Real-time market data
- **NewsAPI** - Financial news aggregation
- **Additional exchanges** - More crypto providers

The provider system is fully extensible - new providers can be added by implementing the `BaseProvider` interface.

## 🔐 Security & Compliance

- Regional compliance checks (US, EU, UK, JP)
- Automatic disclaimer generation
- Rate limiting and quota management
- Audit logging for all requests
- No financial advice - information only

## 📈 Monitoring

Access monitoring dashboards (when Docker services are running):

- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health
- **Prometheus Metrics**: http://localhost:8000/metrics
- **WebSocket Connections**: http://localhost:8000/ws/connections
- **Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **Prometheus UI**: http://localhost:9091
- **Ray Dashboard**: http://localhost:8265
- **MCP Tools**: http://localhost:8000/mcp/tools

## 🧪 Testing

> 📊 **Current Status**: 620/701 tests passing (88.4%) | [Full Test Report](TEST_STATUS_REPORT.md)  
> ✅ Core FIML: 100% passing | ⚠️ Bot Platform: 41 failures (fixes available)  
> 🤖 **Quick Fix**: See [AI Fix Prompts](AI_FIX_PROMPTS.md) for automated solutions

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

### Test Coverage

- **Total Tests**: 701 collected
- **✅ Passing**: 620 tests (88.4%) - All core FIML functionality
- **❌ Failing**: 41 tests (5.8%) - Bot education platform only
- **⏭️ Skipped**: 28 tests (4.0%)
- **Coverage**: 67% of codebase
- **Core Quality**: Production-ready (100% core tests passing)

**Module Status**:
- ✅ Core components (97%+ coverage) - **100% tests passing**
- ✅ Data providers (73% avg coverage) - **100% tests passing**
- ✅ Arbitration engine (59% coverage) - **100% tests passing**
- ✅ MCP protocol (89% coverage) - **100% tests passing**
- ✅ WebSocket streaming (85% coverage) - **100% tests passing**
- ✅ Compliance framework (92% coverage) - **100% tests passing**
- ⚠️ Bot education platform - **41 tests failing** (fixes available)

### Test Documentation

Comprehensive test analysis and fix guides available:

- 📋 **[QUICKSTART_TEST_FIXES.md](QUICKSTART_TEST_FIXES.md)** - Start here! Quick summary and action plan
- 📊 **[TEST_STATUS_REPORT.md](TEST_STATUS_REPORT.md)** - Detailed test analysis and breakdown
- 🤖 **[AI_FIX_PROMPTS.md](AI_FIX_PROMPTS.md)** - 22 ready-to-use AI prompts to fix all failures
- 📚 **[TEST_DOCUMENTATION_INDEX.md](TEST_DOCUMENTATION_INDEX.md)** - Complete documentation index
- 📖 **[TESTING_QUICKSTART.md](TESTING_QUICKSTART.md)** - Original testing guide
- 📈 **[TEST_REPORT.md](TEST_REPORT.md)** - Historical test baseline

See [TEST_STATUS_REPORT.md](TEST_STATUS_REPORT.md) for detailed coverage and [TECHNICAL_STRATEGIC_EVALUATION.md](TECHNICAL_STRATEGIC_EVALUATION.md) for comprehensive analysis.

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

### 🚧 Phase 2 (November 2025 - Q1 2026) - Enhancement & Scale **IN PROGRESS**
- [x] Complete multi-agent implementations ✅ (7 specialized agents with real data)
- [x] Narrative generation engine ✅ (Azure OpenAI integration, 500+ lines)
- [x] Cache warming and predictive optimization ✅ (Implemented with metrics)
- [x] Session management system ✅ (Redis + PostgreSQL dual storage)
- [x] Watchdog event stream orchestration ✅ (Real-time monitoring)
- [x] Performance testing suite ✅ (Benchmarks, load tests, regression detection)
- [ ] Additional data providers (Polygon.io, NewsAPI, IEX Cloud)
- [ ] Platform integrations (ChatGPT GPT, Claude Desktop, Telegram bot)
- [ ] Multi-language support (5+ languages)
- [ ] Security hardening and penetration testing

**Phase 2 Status**: 60% Complete - Core features implemented, integrations pending

### 📋 Phase 3 (Q4 2025) - Scale & Platform
- [ ] Multi-language support
- [ ] Advanced analytics and ML models
- [ ] Backtesting framework for strategy validation
- [ ] Platform integrations (ChatGPT, Claude, Telegram)
- [ ] Performance optimization
- [ ] Enterprise features
- [ ] Extended market coverage

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
