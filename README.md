# FIML - Financial Intelligence Meta-Layer

**The Future of Financial MCP: A "Meta-Layer" That Sits Above All Data Providers**

> 📋 **Project Status**: [View Current Status](STATUS.md) | [Detailed Report](PROJECT_STATUS.md)
> 
> **Build**: ✅ Successful | **Tests**: ⚠️ 5/14 Passing (Core stable) | **Version**: 0.1.0

---

FIML is a 10-year, extensible, AI-native, multi-market financial intelligence framework built on the Model Context Protocol (MCP). It provides intelligent data arbitration, multi-source fusion, and context-aware analysis for AI agents across all platforms.

## 🌟 Key Features

- **🔀 Intelligent Data Arbitration**: Automatically routes queries to optimal providers with fallback strategies
- **⚡ Ultra-Fast Response**: L1 (10-100ms) and L2 (300-700ms) cache layers with predictive pre-warming
- **🌐 Multi-Market Support**: Equities, crypto, forex, commodities, and derivatives across global markets
- **🤖 Multi-Agent Orchestration**: Specialized worker agents for fundamentals, technicals, sentiment, macro, and more
- **📊 Financial Knowledge DSL**: Domain-specific language for complex multi-step queries
- **🔄 Real-Time Intelligence**: WebSocket/SSE event streaming for market anomalies and alerts
- **🛡️ Compliance-First**: Built-in regional compliance, disclaimers, and safety frameworks
- **🌍 Multi-Language**: Narrative generation in 20+ languages
- **📈 Stateful Sessions**: Persistent analysis contexts for multi-turn investigations

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

- **Core**: Python 3.11+, FastAPI, Starlette
- **Protocol**: Model Context Protocol (MCP)
- **Cache**: Redis (L1), PostgreSQL + TimescaleDB (L2)
- **Orchestration**: Ray, Celery, Temporal
- **Event Streaming**: Apache Kafka
- **Analytics**: TA-Lib, pandas-ta, scikit-learn
- **Monitoring**: Prometheus, Grafana, Sentry
- **Container**: Docker, Kubernetes

## 📊 Data Providers

- **Equities**: Alpha Vantage, FMP, Yahoo Finance, Polygon
- **Crypto**: CCXT (Binance, Coinbase, Kraken, etc.)
- **Macro**: FRED, World Bank, ECB
- **News**: NewsAPI, Finnhub, custom scrapers
- **Custom**: Extensible provider interface

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

### Phase 1 (Q1 2025) - Foundation ✅
- Core MCP server implementation
- Data arbitration engine
- Basic provider support (equities, crypto)
- L1/L2 cache system

### Phase 2 (Q2 2025) - Intelligence
- FK-DSL implementation
- Multi-agent orchestration
- Real-time event system
- Stateful sessions

### Phase 3 (Q3 2025) - Scale
- Advanced analytics
- Multi-market expansion
- Predictive caching
- Performance optimization

### Phase 4 (Q4 2025) - Platform
- Mobile/Web clients
- Telegram/WhatsApp bots
- GPT Marketplace integration
- Enterprise features

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
