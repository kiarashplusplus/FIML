# FIML Testing Documentation Index

**Last Updated:** November 25, 2025

## 🎯 Quick Links

### Run Tests

```bash
# Live integration tests (all services)
./scripts/test_live_system.sh

# Live demo (quick showcase)
./live_demo.sh

# Unit/integration tests (pytest)
./check_test_status.sh

# Pre-push validation
./scripts/pre-push-hook.sh
```

### Python Demo Scripts

```bash
# Basic usage examples
python examples/basic_usage.py

# Session management
python examples/session_demo.py

# MCP narrative demo
python examples/mcp_narrative_demo.py

# Watchdog monitoring
python examples/watchdog_demo.py

# WebSocket streaming
python examples/websocket_demo.py
```

## 📚 Test Documentation

### Current Test Results

| Document | Description | Date |
|----------|-------------|------|
| [LIVE_INTEGRATION_TEST_RESULTS.md](./LIVE_INTEGRATION_TEST_RESULTS.md) | Latest live system integration tests | Nov 25, 2025 |
| [MCP_TOOLS_TEST_RESULTS.md](./MCP_TOOLS_TEST_RESULTS.md) | MCP Protocol tools testing (9/9 tools) | Nov 25, 2025 |
| [TEST_STATUS_REPORT.md](./TEST_STATUS_REPORT.md) | Comprehensive pytest results (701 tests) | Nov 24, 2025 |
| [LIVE_TEST_SUMMARY.md](../implementation-summaries/LIVE_TEST_SUMMARY.md) | Live provider validation summary | Earlier |

### Testing Guides

| Document | Purpose |
|----------|---------|
| [TESTING_QUICKSTART.md](./TESTING_QUICKSTART.md) | Quick start guide for testing |
| [TEST_DOCUMENTATION_INDEX.md](./TEST_DOCUMENTATION_INDEX.md) | Detailed test documentation index |
| [QUICKSTART_TEST_FIXES.md](./QUICKSTART_TEST_FIXES.md) | Common test issues and fixes |

### Infrastructure & Performance

| Document | Focus |
|----------|-------|
| [TEST_INFRASTRUCTURE_IMPROVEMENT.md](./TEST_INFRASTRUCTURE_IMPROVEMENT.md) | Test infrastructure improvements |
| [Performance Testing Guide](../../development/PERFORMANCE_TESTING.md) | Performance testing guide |

### Historical Reports

| Document | Coverage |
|----------|----------|
| [TEST_REPORT.md](./TEST_REPORT.md) | Historical test reports |
| [PHASE1_TEST_COVERAGE_SUMMARY.md](../implementation-summaries/PHASE1_TEST_COVERAGE_SUMMARY.md) | Phase 1 coverage |

## 🧪 Testing Scripts

### Shell Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `test_live_system.sh` | Comprehensive live system tests | `scripts/` |
| `live_demo.sh` | Quick demo of capabilities | Root |
| `check_test_status.sh` | Pytest test runner and summary | Root |
| `pre-push-hook.sh` | Pre-commit validation | `scripts/` |

### Python Examples

| Example | Focus | Location |
|---------|-------|----------|
| `basic_usage.py` | MCP tools basics | `examples/` |
| `session_demo.py` | Session management | `examples/` |
| `mcp_narrative_demo.py` | Narrative generation | `examples/` |
| `watchdog_demo.py` | Monitoring & alerts | `examples/` |
| `websocket_demo.py` | Real-time updates | `examples/` |
| `websocket_streaming.py` | Streaming data | `examples/` |
| `dashboard_alerts_demo.py` | Dashboard & alerts | `examples/` |
| `agent_workflows_demo.py` | Agent workflows | `examples/` |
| `bot_demo.py` | Educational bot | `examples/` |
| `narrative_demo.py` | Narrative system | `examples/` |
| `lesson_content_demo.py` | Lesson content | `examples/` |
| `lesson_version_migration_demo.py` | Version migration | `examples/` |

## 📊 Test Coverage Summary

### Latest Integration Tests (Nov 25, 2025)
- **Total Tests:** 22
- **Passed:** 22 (100%)
- **Failed:** 0
- **Categories:** Health, API, Dashboard, MCP, WebSocket, Infrastructure, Celery

### Pytest Suite (Nov 24, 2025)
- **Total Tests:** 701
- **Passed:** 665 (94.9%)
- **Failed:** 8 (1.1%)
- **Skipped:** 28 (4.0%)
- **Code Coverage:** 54%

## 🎯 Test Types

### 1. Live Integration Tests
**Script:** `./scripts/test_live_system.sh`

Tests all running services with real HTTP requests:
- Health endpoints (API, DB, Cache, Providers)
- API documentation (OpenAPI, Swagger)
- Dashboard endpoints
- MCP Protocol (stock/crypto searches, sessions)
- WebSocket connections
- Infrastructure (Redis, PostgreSQL, Kafka, Ray, Grafana, Prometheus)
- Celery task queue

### 2. Unit & Integration Tests
**Script:** `./check_test_status.sh`

Comprehensive pytest suite covering:
- Core framework (17 tests)
- MCP protocol (67 tests)
- Data providers (149 tests)
- Cache system (113 tests)
- Agents (39 tests)
- Arbitration (19 tests)
- And more...

### 3. Live Demos
**Script:** `./live_demo.sh`

Quick demonstration of:
- System health
- MCP tools
- Stock data (AAPL, TSLA)
- Crypto data (BTC)
- Running services

### 4. Example Scripts
**Location:** `examples/`

Interactive Python examples for:
- API usage
- Session management
- WebSocket streaming
- Dashboard integration
- Agent workflows
- Bot functionality

## 🔧 Development Testing

### Pre-Push Hook
**Script:** `./scripts/pre-push-hook.sh`

Runs before git push:
1. ✅ Black code formatting
2. ✅ Ruff linting
3. ✅ Pytest suite (non-Docker tests)

### Manual Testing Workflow

```bash
# 1. Start the system
./quickstart.sh

# 2. Wait for services to be ready
sleep 30

# 3. Run comprehensive tests
./scripts/test_live_system.sh

# 4. Run pytest suite
./check_test_status.sh

# 5. Run live demo
./live_demo.sh

# 6. Test specific examples
python examples/basic_usage.py
python examples/session_demo.py
```

## 📈 Test Results Locations

### Generated Files
- `docs/testing/LIVE_INTEGRATION_TEST_RESULTS.md` - Latest integration test results
- `.pytest_cache/` - Pytest cache
- `htmlcov/` - Coverage HTML reports (if generated)

### CI/CD
- GitHub Actions workflows in `.github/workflows/`
- Pre-push hooks in `.git/hooks/` (after running `scripts/install-hooks.sh`)

## 🚀 Getting Started

### First Time Setup

```bash
# 1. Install development dependencies
pip install -e ".[dev]"

# 2. Install git hooks
./scripts/install-hooks.sh

# 3. Start the system
./quickstart.sh

# 4. Run tests
./scripts/test_live_system.sh
```

### Daily Development

```bash
# Quick test before committing
./check_test_status.sh

# Full integration test
./scripts/test_live_system.sh

# Demo to verify
./live_demo.sh
```

## 📖 Additional Resources

- **CONTRIBUTING.md** - Contribution guidelines (see repo root)
- **README.md** - Main documentation (see repo root)
- **DEPLOYMENT.md** - Deployment guide (see repo root)
- [Contributing Guidelines](../../development/contributing.md) - Development documentation
- [Testing Documentation](index.md) - Testing resources

## 🔍 Finding Specific Tests

### By Component
- **MCP Protocol:** `tests/test_mcp*.py`
- **Providers:** `tests/test_providers*.py`
- **Cache:** `tests/test_cache*.py`
- **Agents:** `tests/test_agents*.py`
- **Bot:** `tests/test_bot*.py`
- **Dashboard:** `tests/test_dashboard*.py`
- **WebSocket:** `tests/test_websocket*.py`

### By Type
- **Unit Tests:** Most files in `tests/`
- **Integration Tests:** `tests/test_*_comprehensive.py`
- **E2E Tests:** `tests/test_*_e2e.py`
- **Live Tests:** `scripts/test_live_system.sh`

## ⚙️ Environment Variables for Testing

```bash
# Set in .env for testing
FIML_ENV=development
FIML_LOG_LEVEL=INFO

# Mock credentials for tests
AZURE_OPENAI_API_KEY=mock-api-key-for-testing
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

---

**Note:** This index is maintained to help developers quickly find and run the appropriate tests for their work. Always run `./scripts/test_live_system.sh` before major commits or releases.
