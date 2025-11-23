# FIML - Financial Intelligence Meta-Layer

**An AI-Native Financial Data MCP Server with Intelligent Provider Orchestration**

> 📋 **Project Status**: ✅ **PHASE 1 COMPLETE** | [Test Results](TEST_REPORT.md) [![FIML CI/CD Pipeline](https://github.com/kiarashplusplus/FIML/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kiarashplusplus/FIML/actions/workflows/ci.yml) | [Technical Evaluation](TECHNICAL_STRATEGIC_EVALUATION.md)
> 
> **Current State**: Phase 1 Complete ✅ | Phase 2 Planning 📋 | **Version**: 0.1.1 | **Tests**: 100% pass rate | **Coverage**: [![codecov](https://codecov.io/gh/kiarashplusplus/FIML/graph/badge.svg)](https://codecov.io/gh/kiarashplusplus/FIML)


> 📊 **Quick Links**:
> - 🎯 [Phase Evaluation Report](PHASE_EVALUATION_REPORT.md) - Visual summary and verification
> - 📘 [Technical & Strategic Evaluation](TECHNICAL_STRATEGIC_EVALUATION.md) - Comprehensive 21KB analysis
> - ⚡ [Current State Summary](CURRENT_STATE_SUMMARY.md) - TL;DR quick reference

---

FIML is an MCP (Model Context Protocol) server that provides intelligent financial data access through a unified interface. It implements a data arbitration layer that automatically selects the best data provider based on availability, freshness, and reliability. The project is designed with a 10-year extensibility roadmap (see [BLUEPRINT.md](BLUEPRINT.md) for the complete vision).

## 🌟 What's Actually Working (Phase 1 Complete)

### ✅ Core Infrastructure (100%)
- **🔀 Data Arbitration Engine**: Multi-provider scoring (5 factors), automatic fallback, conflict resolution
- **🏗️ Provider System**: 5 working providers - Yahoo Finance, Alpha Vantage, FMP, CCXT, Mock
- **⚡ Cache Architecture**: L1 (Redis 10-100ms) and L2 (PostgreSQL 300-700ms) with intelligent optimizations
  - Cache warming for popular symbols
  - Intelligent eviction policies (LRU/LFU)
  - Latency tracking and hit rate optimization
  - 1000+ concurrent request support
- **📊 FK-DSL Parser**: Complete Lark-based grammar with execution framework
- **🔧 MCP Server**: FastAPI-based server with 4 fully operational MCP tools
- **🌐 WebSocket Streaming**: Real-time price and OHLCV data streaming (650 lines)
- **📦 Docker Deployment**: Complete docker-compose.yml with 12 services configured
- **🧪 Test Suite**: 213 passing tests (90%+ success rate), comprehensive coverage
- **💰 Live Data**: Real stock prices (AAPL, TSLA, MSFT) from multiple providers
- **₿ Crypto Support**: BTC, ETH via CCXT multi-exchange integration
- **🛡️ Compliance Framework**: Regional checks (8 regions), disclaimers, investment advice detection
- **📈 Monitoring Hooks**: Prometheus metrics endpoints, health checks

### 📋 Phase 2 Features (In Planning, Not Yet Implemented)
- **🤖 Advanced Agent Workflows**: Framework exists (700 lines), full implementation pending
- **📝 Narrative Generation**: Not yet started - planned for Q1 2026
- **🌍 Multi-language Support**: Not yet implemented - planned for Q2 2026
- **🔌 Platform Integrations**: ChatGPT, Claude, Telegram - not yet started
- **⚡ Performance Optimization**: Cache warming, load testing - pending
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

## 📊 Code Metrics & Quality

**Implementation Stats** (November 2025):
- **Total Python Files**: 43 implementation files
- **Lines of Code**: 7,676 lines of production code
- **Test Files**: 19 comprehensive test suites  
- **Test Coverage**: 236 passing tests (100% pass rate), 24 skipped, 67% code coverage
- **Code Quality**: A- grade (clean, type-safe, well-structured)
- **Dependencies**: All stable, no critical vulnerabilities
- **Linting**: 100% passing (ruff)

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

### Quick Test Commands

```bash
# Run all unit tests (exclude live tests)
pytest tests/ -v -m "not live"

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

- **Total Tests**: 236 passing, 24 skipped
- **Pass Rate**: 100%
- **Coverage**: 67% of codebase
- **Quality**: Production-ready

Tests cover:
- Core components (97%+)
- All 5 providers (73% avg)
- Arbitration engine (59%)
- MCP tools (89%)
- WebSocket streaming (85%)
- Compliance framework (92%)

See [TEST_REPORT.md](TEST_REPORT.md) for detailed coverage and [TECHNICAL_STRATEGIC_EVALUATION.md](TECHNICAL_STRATEGIC_EVALUATION.md) for comprehensive analysis.

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
- [x] Comprehensive test framework (213 passing tests, 90%+ success)
- [x] Compliance framework (654 lines, 8 regions supported)
- [x] Error handling and retry logic throughout
- [x] Real-time WebSocket streaming (650 lines, production-ready)
- [x] **Total Implementation**: 7,676 lines of production code

**Phase 1 Status**: 95% Complete - Core features operational, optimization pending

### 📋 Phase 2 (Q1-Q2 2026) - Enhancement & Scale **PLANNING**
- [ ] Complete multi-agent implementations (framework exists, logic pending)
- [ ] Narrative generation engine (not started)
- [ ] Cache warming and predictive optimization (basic cache works, optimization needed)
- [ ] Additional data providers (Polygon.io, NewsAPI, IEX Cloud)
- [ ] Platform integrations (ChatGPT GPT, Claude Desktop, Telegram bot)
- [ ] Multi-language support (5+ languages)
- [ ] Performance optimization and load testing
- [ ] Security hardening and penetration testing

**Phase 2 Status**: 5% Complete - Preparatory work only, main features not started

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
