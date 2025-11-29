# CI/CD Pipeline Test Strategy

This document describes how the FIML test suite is organized across GitHub Actions workflows to optimize CI performance and reliability.

## Test Categories

### 1. Fast Unit Tests (Default)
**Marker:** `not integration`  
**Execution Time:** ~94 seconds  
**Command:** `make test` or `pytest -m "not integration"`

These are the default tests that run on every commit and PR. They:
- Skip tests requiring Ray cluster (`@pytest.mark.integration`)
- Mock external API calls (yfinance, CCXT, Azure OpenAI)
- Use local Redis/PostgreSQL services

### 2. Integration Tests
**Marker:** `@pytest.mark.integration`  
**Execution Time:** Varies (requires Ray cluster setup)  
**Command:** `make test-integration` or `pytest -m integration`

These tests require full infrastructure:
- Ray cluster for multi-agent orchestration
- Complete end-to-end workflows
- Real component interactions

Currently includes:
- `tests/test_agent_workflows.py::test_end_to_end_equity_workflow`
- `tests/test_agent_workflows.py::test_end_to_end_crypto_workflow`

## CI Workflow Organization

### Component-Specific Fast Workflows

All component workflows **skip integration tests** to maintain fast feedback (<5 min):

| Workflow | Coverage | Test Filter |
|----------|----------|-------------|
| `ci.yml` | Core + Cache | Explicit file list |
| `test-core.yml` | Core + Cache | Explicit file list |
| `test-providers.yml` | Providers | `--cov=fiml.providers` |
| `test-arbitration.yml` | Arbitration | `--cov=fiml.arbitration` |
| `test-dsl.yml` | DSL | `--cov=fiml.dsl` |
| `test-mcp.yml` | MCP | `--cov=fiml.mcp` |
| `test-agents.yml` | Agents + Narrative | `-m "not integration"` ⚡ |
| `test-infrastructure.yml` | Infrastructure | `--cov=...` |
| `test-bot.yml` | Bot | `--cov=fiml.bot` |

⚡ **Updated:** Added marker filter to exclude integration tests

### Integration Test Workflow

`test-integration.yml` runs **only integration tests** on a schedule:

```yaml
- name: Run Integration tests
  run: |
    pytest -v --cov=fiml --cov-report=xml --cov-report=term --no-docker \
      -m integration \
      tests/
```

**Triggers:**
- Daily at midnight (cron: `0 0 * * *`)
- Manual workflow dispatch
- Pull requests (optional)

## Updated Workflows

### `test-agents.yml` 
✅ **Updated** to exclude integration tests:
```yaml
pytest -v ... -m "not integration" tests/test_agent_workflows.py ...
```

This prevents Ray connection timeouts in CI since Ray cluster is not available.

### `test-integration.yml`
✅ **Updated** to use marker-based filtering:
```yaml
pytest -v ... -m integration tests/
```

This auto-discovers all tests marked with `@pytest.mark.integration` instead of maintaining an explicit file list.

## Local Development

### Daily Development
```bash
# Fast unit tests (recommended for TDD)
make test

# Run specific component tests
pytest tests/test_arbitration.py -v
```

### Before Committing
```bash
# Fast validation
make test

# If modifying agent workflows, run integration tests
make test-integration
```

### Full Validation
```bash
# Complete suite
make test-all
```

## Adding New Integration Tests

When adding tests that require Ray or full infrastructure:

1. Mark the test with `@pytest.mark.integration`:
   ```python
   @pytest.mark.integration
   async def test_my_integration_workflow():
       # Test requiring Ray cluster
       pass
   ```

2. The test will:
   - Be **skipped** in `make test` and component workflows
   - Run in `test-integration.yml` daily workflow
   - Be available via `make test-integration` locally

3. No CI workflow updates needed - marker-based filtering handles it automatically

## Performance Benchmarks

| Test Suite | Before | After | Speedup |
|------------|--------|-------|---------|
| **Unit Tests** | 871s (14m 31s) | 94s (1m 34s) | **9.3x** |
| **Agent Tests** | ~300s+ (w/ Ray timeout) | ~30s | **10x+** |

## CI Health Indicators

✅ **Good:**
- Component workflows complete in <5 minutes
- No Ray connection timeouts
- High test pass rate

⚠️ **Issues:**
- Integration tests failing (check Ray cluster)
- Component tests timing out (check for unmarked integration tests)
- Coverage drops (tests may be getting skipped incorrectly)
