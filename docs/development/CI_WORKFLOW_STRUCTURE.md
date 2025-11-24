# CI Workflow Structure

This document describes the new component-based CI/CD workflow structure for FIML.

## Overview

The CI/CD pipeline has been reorganized from a single monolithic workflow into 9 specialized workflows. This provides:

- **Faster feedback** - Core tests run on every commit
- **Better diagnostics** - Easy to identify which component is failing
- **Parallel execution** - Independent test suites run in parallel
- **Efficient resource usage** - Only run relevant tests based on changed files

## Workflow Files

### 1. `ci.yml` - Main CI Pipeline (Core Tests Only)
**Triggers:** Every push and PR to main/develop
**Tests:** Core functionality and cache tests only
**Purpose:** Fast feedback loop for fundamental functionality

```yaml
Tests:
- test_core.py (15 tests)
- test_cache.py (18 tests) 
- test_cache_improved.py (14 tests)
- test_cache_optimizations.py (17 tests)
Total: 64 tests
```

### 2. `test-core.yml` - Core Component Tests
**Triggers:** All commits
**Coverage:** `fiml/core/`, `fiml/cache/`
**Badge:** Core tests always run and should always pass

### 3. `test-providers.yml` - Data Provider Tests
**Triggers:** PRs that change provider code or tests
**Coverage:** `fiml/providers/`
**Tests:**
- test_providers.py
- test_providers_advanced.py
- test_provider_registry.py
- test_new_providers.py
- test_phase2_providers.py
- test_newsapi_integration.py

### 4. `test-arbitration.yml` - Provider Arbitration Tests
**Triggers:** PRs that change arbitration code or tests
**Coverage:** `fiml/arbitration/`
**Tests:**
- test_arbitration.py
- test_arbitration_advanced.py
- test_arbitration_coverage.py

### 5. `test-dsl.yml` - DSL Parser Tests
**Triggers:** PRs that change DSL code or tests
**Coverage:** `fiml/dsl/`
**Tests:**
- test_dsl_advanced.py
- test_dsl_coverage.py

### 6. `test-mcp.yml` - MCP Server Tests
**Triggers:** PRs that change MCP/server code or tests
**Coverage:** `fiml/mcp/`, `fiml/server.py`
**Tests:**
- test_mcp_and_server.py
- test_mcp_coverage.py
- test_server.py

### 7. `test-agents.yml` - Agent Workflow Tests
**Triggers:** PRs that change agent/narrative code or tests
**Coverage:** `fiml/agents/`, `fiml/narrative/`
**Tests:**
- test_agents.py
- test_agent_workflows.py
- test_narrative.py
- test_narrative_generation.py
- test_mcp_narrative_integration.py

### 8. `test-infrastructure.yml` - Infrastructure Tests
**Triggers:** PRs that change infrastructure code or tests
**Coverage:** `fiml/compliance/`, `fiml/alerts/`, `fiml/watchdog/`, `fiml/sessions/`, `fiml/tasks/`, `fiml/websocket/`
**Tests:**
- test_compliance.py
- test_alerts.py
- test_watchdog.py
- test_sessions.py
- test_tasks.py
- test_websocket.py
- test_workers_integration.py

### 9. `test-integration.yml` - Integration Tests
**Triggers:** 
- All PRs
- Daily schedule (midnight UTC)
- Manual workflow dispatch
**Coverage:** Full application integration
**Tests:**
- test_integration.py
- test_e2e_api.py
- test_dashboard.py
- test_azure_openai.py

Note: `test_live_system.py` is excluded as it requires live external services.

## Test Execution Matrix

| Workflow | On Push | On PR | On Schedule | Path Triggers |
|----------|---------|-------|-------------|---------------|
| ci.yml (core) | ✅ | ✅ | ❌ | All |
| test-core.yml | ✅ | ✅ | ❌ | All |
| test-providers.yml | ❌ | ✅ | ❌ | fiml/providers/**, tests/test_providers* |
| test-arbitration.yml | ❌ | ✅ | ❌ | fiml/arbitration/**, tests/test_arbitration* |
| test-dsl.yml | ❌ | ✅ | ❌ | fiml/dsl/**, tests/test_dsl* |
| test-mcp.yml | ❌ | ✅ | ❌ | fiml/mcp/**, fiml/server.py, tests/test_mcp*, tests/test_server.py |
| test-agents.yml | ❌ | ✅ | ❌ | fiml/agents/**, fiml/narrative/**, tests/test_agents*, tests/test_narrative* |
| test-infrastructure.yml | ❌ | ✅ | ❌ | fiml/{compliance,alerts,watchdog,sessions,tasks,websocket}/** |
| test-integration.yml | ❌ | ✅ | ✅ Daily | All |

## Benefits

### 1. Faster Feedback
- Core tests complete in ~1 minute
- No waiting for full test suite on every commit
- Quick identification of core functionality issues

### 2. Better Resource Utilization
- Only run tests relevant to changed code
- Parallel execution of independent test suites
- Reduced CI/CD costs

### 3. Clearer Status
- Core workflow badge shows fundamental health
- Component-specific failures are isolated
- Easier to diagnose and fix issues

### 4. Developer Experience
- Less noise from unrelated test failures
- Can manually trigger specific test suites
- Integration tests run on schedule to catch issues early

## Usage

### For Contributors

**On every commit:**
- Core tests run automatically
- Must pass for merge

**On pull requests:**
- Core tests + relevant component tests run
- Based on which files were changed
- All applicable tests must pass

**Manual testing:**
You can trigger specific test suites manually:
```bash
# Run core tests locally
pytest tests/test_core.py tests/test_cache*.py

# Run provider tests locally  
pytest tests/test_providers*.py tests/test_newsapi*.py

# Run all tests
pytest tests/
```

### For Maintainers

**Monitoring:**
- Check core workflow badge for overall health
- Review component-specific workflow results in PRs
- Daily integration test runs catch integration issues

**Debugging:**
- Failed core tests → fundamental issue
- Failed component tests → isolated to that component
- Failed integration tests → cross-component issue

## Coverage Reporting

Each workflow uploads coverage to Codecov with specific flags:
- `core` - Core and cache coverage
- `providers` - Provider coverage
- `arbitration` - Arbitration coverage
- `dsl` - DSL coverage
- `mcp` - MCP server coverage
- `agents` - Agent and narrative coverage
- `infrastructure` - Infrastructure coverage
- `integration` - Full integration coverage

This allows tracking coverage per component over time.

## Migration Notes

**Before:**
- Single `ci.yml` ran all 35 test files (~439 tests)
- Any test failure blocked the entire pipeline
- Long execution time (~5-10 minutes)

**After:**
- Core workflow runs 4 test files (64 tests) in ~1 minute
- Component tests run in parallel on PRs
- Total time reduced, better parallelization
- Isolated failure domains

## Future Improvements

- [ ] Add performance test workflows
- [ ] Add security scanning workflows
- [ ] Implement test result caching
- [ ] Add benchmark comparison workflows
- [ ] Create nightly comprehensive test runs
