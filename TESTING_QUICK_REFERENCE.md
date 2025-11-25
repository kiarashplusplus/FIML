# FIML Testing Resources - Quick Reference

## 🎯 All Test Scripts & Commands

### Live System Testing

```bash
# Comprehensive integration tests (22 tests)
./scripts/test_live_system.sh

# Quick demo (6 quick checks)
./live_demo.sh

# Unit/integration tests (701 tests via pytest)
./check_test_status.sh
```

### Python Demo Examples

```bash
# All examples are in the examples/ directory
python examples/basic_usage.py              # MCP tools basics
python examples/session_demo.py             # Session management
python examples/mcp_narrative_demo.py       # Narrative generation
python examples/watchdog_demo.py            # Monitoring & alerts
python examples/websocket_demo.py           # Real-time updates
python examples/websocket_streaming.py      # Streaming data
python examples/dashboard_alerts_demo.py    # Dashboard integration
python examples/agent_workflows_demo.py     # Agent workflows
python examples/bot_demo.py                 # Educational bot features
python examples/narrative_demo.py           # Narrative system
python examples/lesson_content_demo.py      # Lesson content
python examples/lesson_version_migration_demo.py  # Version migration
```

## 📊 Test Documentation

### Primary Test Results (Latest → Oldest)

1. **LIVE_INTEGRATION_TEST_RESULTS.md** (Nov 25, 2025) ✨ NEW
   - Location: `docs/testing/LIVE_INTEGRATION_TEST_RESULTS.md`
   - 22/22 tests passed (100%)
   - Tests all Docker services, APIs, MCP protocol
   - Live stock/crypto data validation

2. **TEST_STATUS_REPORT.md** (Nov 24, 2025)
   - Location: `docs/testing/TEST_STATUS_REPORT.md`
   - 665/701 tests passed (94.9%)
   - Comprehensive pytest coverage
   - 54% code coverage

3. **LIVE_TEST_SUMMARY.md** (Earlier)
   - Location: `docs/implementation-summaries/LIVE_TEST_SUMMARY.md`
   - 140/169 tests passed (83%)
   - Real provider integration validation

### Testing Guides

- **TESTING_INDEX.md** ✨ NEW - Complete testing documentation index
- **TESTING_QUICKSTART.md** - Quick start guide
- **QUICKSTART_TEST_FIXES.md** - Common issues and solutions
- **TEST_DOCUMENTATION_INDEX.md** - Detailed documentation index

## 🔧 Scripts Inventory

### Shell Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `test_live_system.sh` | `scripts/` | **NEW** - Live integration tests |
| `live_demo.sh` | Root | Quick demo showcase |
| `check_test_status.sh` | Root | Pytest runner with summary |
| `quickstart.sh` | Root | Start all services |
| `pre-push-hook.sh` | `scripts/` | Pre-commit validation |
| `install-hooks.sh` | `scripts/` | Install git hooks |

### Python Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| 12 demo files | `examples/` | Interactive demonstrations |
| `setup_session_db.py` | `scripts/` | Database initialization |
| `load_test_cache.py` | `scripts/` | Populate test data |

## 📁 File Organization Changes

### Moved Files

```
✅ TEST_RESULTS.md → docs/testing/LIVE_INTEGRATION_TEST_RESULTS.md
✅ test_system.sh → scripts/test_live_system.sh
```

### New Files

```
✨ docs/testing/TESTING_INDEX.md - Complete testing documentation index
✨ TESTING_QUICK_REFERENCE.md - This file
```

### Updated Files

```
✏️ live_demo.sh - Added reference to test_live_system.sh
✏️ scripts/README.md - Added test script documentation
```

## 🚀 Recommended Testing Workflow

### After Starting Services

```bash
# 1. Start the system
./quickstart.sh

# 2. Wait for services
sleep 30

# 3. Run comprehensive live tests
./scripts/test_live_system.sh

# 4. Quick demo
./live_demo.sh
```

### Development Testing

```bash
# Before committing
./check_test_status.sh

# Before pushing (automatic if hooks installed)
./scripts/pre-push-hook.sh

# Test specific functionality
python examples/basic_usage.py
```

### Full Validation

```bash
# Complete test suite
./scripts/test_live_system.sh  # Live integration
./check_test_status.sh         # Pytest suite
./live_demo.sh                 # Demo
python examples/*.py           # All demos
```

## 📈 Test Coverage Summary

| Test Suite | Tests | Pass Rate | Coverage |
|------------|-------|-----------|----------|
| Live Integration | 22 | 100% | All services |
| Pytest Suite | 701 | 94.9% | 54% code |
| Live Provider Tests | 169 | 83% | Real APIs |

## 🔍 Finding Tests

### By Component

```bash
# MCP Protocol
pytest tests/test_mcp*.py

# Providers
pytest tests/test_providers*.py

# Cache
pytest tests/test_cache*.py

# All bot tests
pytest tests/test_bot*.py
```

### By Type

```bash
# Unit tests
pytest tests/ -m "not live"

# Live tests
./scripts/test_live_system.sh

# Specific module
pytest tests/test_agents.py -v
```

## 📖 Documentation Links

- [Main Index](docs/testing/TESTING_INDEX.md) - Complete testing documentation
- [Test Results](docs/testing/LIVE_INTEGRATION_TEST_RESULTS.md) - Latest results
- [Test Status](docs/testing/TEST_STATUS_REPORT.md) - Pytest coverage
- [Scripts README](scripts/README.md) - Script documentation

## ⚡ Quick Commands

```bash
# Most common commands
./scripts/test_live_system.sh    # Full integration test
./live_demo.sh                   # Quick demo
./check_test_status.sh           # Pytest suite
python examples/basic_usage.py   # Basic MCP usage
python examples/session_demo.py  # Session management
```

---

**Last Updated:** November 25, 2025  
**Total Test Scripts:** 3 shell + 12 Python demos  
**Total Test Docs:** 10+ documentation files  
**Test Coverage:** 100% live integration, 94.9% pytest, 54% code
