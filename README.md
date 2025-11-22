# FIML - Financial Intelligence Meta-Layer

**An AI-Native Financial Data MCP Server with Intelligent Provider Orchestration**

> 📋 **Project Status**: [View Current Status](STATUS.md) | [Detailed Report](PROJECT_STATUS.md)
> 
> **Current Phase**: 1 (Foundation) - Core Infrastructure Complete | **Version**: 0.1.0

---

FIML is an MCP (Model Context Protocol) server that provides intelligent financial data access through a unified interface. It implements a data arbitration layer that automatically selects the best data provider based on availability, freshness, and reliability. The project is designed with a 10-year extensibility roadmap (see [BLUEPRINT.md](BLUEPRINT.md) for the complete vision).

## 🌟 Current Features (Phase 1)

### ✅ Implemented and Working
- **🔀 Data Arbitration Engine**: Multi-provider scoring, automatic fallback, conflict resolution
- **🏗️ Provider Abstraction**: Pluggable provider architecture (currently: Yahoo Finance, Mock)
- **⚡ Cache Architecture**: L1 (Redis) and L2 (PostgreSQL/TimescaleDB) implementations ready
- **📊 FK-DSL Parser**: Complete Lark-based grammar for financial queries
- **🤖 Agent Framework**: Ray-based multi-agent orchestration structure
- **🔧 MCP Server**: FastAPI-based server with 4 core MCP tools
- **📦 Production Ready**: Docker, Kubernetes, CI/CD configurations
- **🧪 Test Suite**: Unit and integration tests for core components

### 🚧 In Development (Phase 2+)
- **Additional Providers**: Alpha Vantage, FMP, CCXT crypto exchanges
- **Real-time Streaming**: WebSocket/SSE for live market data
- **Advanced Analytics**: Complete multi-agent analysis workflows
- **Compliance Framework**: Regional compliance and risk assessment
- **Narrative Generation**: AI-powered market analysis summaries
- **Multi-language Support**: I18n for global markets

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
git clone https://github.com/your-org/fiml.git
cd fiml
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
- **Mock Provider** ✅ - Testing and development

### Planned (Phase 2)
- **Alpha Vantage** - Fundamentals and premium equity data
- **FMP** (Financial Modeling Prep) - Financial statements
- **CCXT** - Multi-exchange cryptocurrency data
- **Polygon.io** - Real-time market data
- **NewsAPI** - Financial news aggregation

The provider system is fully extensible - new providers can be added by implementing the `BaseProvider` interface.

## 🔐 Security & Compliance

- Regional compliance checks (US, EU, UK, JP)
- Automatic disclaimer generation
- Rate limiting and quota management
- Audit logging for all requests
- No financial advice - information only

## 📈 Monitoring

Access monitoring dashboards:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Ray Dashboard**: http://localhost:8265

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_arbitration.py -v

# Run with coverage
pytest --cov=fiml --cov-report=html
```

## 📝 API Documentation

Once running, access interactive API docs at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🗺️ Roadmap

### ✅ Phase 1 (Q1 2025) - Foundation COMPLETE
- [x] Core MCP server implementation
- [x] Data arbitration engine with scoring and fallback
- [x] Provider abstraction layer
- [x] Basic provider support (Yahoo Finance)
- [x] L1/L2 cache architecture
- [x] FK-DSL parser and execution framework
- [x] Multi-agent orchestration structure
- [x] Docker and Kubernetes deployment
- [x] CI/CD pipeline
- [x] Test framework

### 🚧 Phase 2 (Q2-Q3 2025) - Intelligence Layer
- [ ] Complete provider integrations (Alpha Vantage, FMP, CCXT)
- [ ] Real-time WebSocket streaming
- [ ] Advanced multi-agent workflows
- [ ] Compliance and safety framework
- [ ] Narrative generation engine
- [ ] Cache warming and optimization
- [ ] Enhanced error handling and retry logic

### 📋 Phase 3 (Q4 2025) - Scale & Platform
- [ ] Multi-language support
- [ ] Advanced analytics and ML models
- [ ] Platform integrations (ChatGPT, Claude, Telegram)
- [ ] Performance optimization
- [ ] Enterprise features
- [ ] Extended market coverage

### 🔮 Phase 4+ (2026+) - Ecosystem
See [BLUEPRINT.md](BLUEPRINT.md) for the complete 10-year vision including:
- Plugin ecosystem and Financial OS
- Decentralized data verification
- Advanced quant strategies
- Global market expansion
- AI-native portfolio optimization

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

Built with ♥ for the AI and finance communities

## 📞 Support

- **Documentation**: [docs.fiml.ai](https://docs.fiml.ai)
- **Issues**: [GitHub Issues](https://github.com/your-org/fiml/issues)
- **Discord**: [Join our community](https://discord.gg/fiml)

---

**⚠️ Disclaimer**: FIML provides financial data and analysis for informational purposes only. This is NOT financial advice. Always do your own research and consult with qualified financial advisors before making investment decisions.
