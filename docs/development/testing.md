# Testing Guide

Comprehensive guide to testing FIML components.

## Test Structure

FIML uses pytest for testing with the following structure:

```
tests/
├── conftest.py              # Shared fixtures
├── test_arbitration.py      # Arbitration engine tests
├── test_cache.py            # Cache layer tests
├── test_mcp.py              # MCP tools tests
├── test_providers/          # Provider tests
│   ├── test_yahoo.py
│   ├── test_alpha_vantage.py
│   └── test_ccxt.py
├── test_dsl.py              # FK-DSL parser tests
├── test_websocket.py        # WebSocket tests
└── test_e2e_api.py          # End-to-end API tests
```

## Running Tests

### All Tests

```bash
make test
```

Or using pytest directly:

```bash
pytest tests/ -v
```

### Specific Test File

```bash
pytest tests/test_arbitration.py -v
```

### Specific Test Function

```bash
pytest tests/test_arbitration.py::test_provider_scoring -v
```

### With Coverage

```bash
pytest tests/ --cov=fiml --cov-report=html
```

View coverage report:

```bash
open htmlcov/index.html
```

## Test Categories

### Unit Tests

Test individual components in isolation:

```bash
pytest tests/ -v -m "not live and not slow"
```

Example unit test:

```python
def test_cache_key_generation():
    """Test cache key generation."""
    from fiml.cache import generate_cache_key
    
    key = generate_cache_key("yahoo", "AAPL", "price")
    assert key == "yahoo:AAPL:price"
```

### Integration Tests

Test component interactions:

```bash
pytest tests/test_e2e_api.py -v
```

Example integration test:

```python
@pytest.mark.asyncio
async def test_api_with_cache():
    """Test API endpoint with caching."""
    # First call - cache miss
    response1 = await client.get("/api/price/AAPL")
    assert response1.status_code == 200
    
    # Second call - cache hit
    response2 = await client.get("/api/price/AAPL")
    assert response2.status_code == 200
    assert response2.json() == response1.json()
```

### Live Tests

Tests requiring external services:

```bash
pytest tests/ -v -m live
```

**Note**: Live tests require:
- Docker services running
- Valid API keys configured

Example live test:

```python
@pytest.mark.live
@pytest.mark.asyncio
async def test_live_price_fetch():
    """Test live price fetching from Yahoo Finance."""
    provider = YahooFinanceProvider()
    price = await provider.fetch_price("AAPL")
    
    assert price > 0
    assert isinstance(price, float)
```

### Performance Tests

Benchmark critical paths:

```bash
pytest tests/ -v --benchmark-only
```

Example benchmark:

```python
def test_arbitration_performance(benchmark):
    """Benchmark arbitration scoring."""
    result = benchmark(arbitration_engine.score_providers, "AAPL")
    assert len(result) > 0
```

## Writing Tests

### Test Structure

Follow AAA pattern (Arrange, Act, Assert):

```python
def test_provider_fallback():
    """Test provider fallback on failure."""
    # Arrange
    engine = ArbitrationEngine()
    providers = ["alpha_vantage", "yahoo", "fmp"]
    
    # Act - First provider fails
    result = engine.select_provider("AAPL", providers)
    
    # Assert
    assert result in providers
    assert result != "alpha_vantage"  # First provider should be skipped
```

### Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
async def api_client():
    """Provide async API client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_endpoint(api_client):
    """Test API endpoint."""
    response = await api_client.get("/health")
    assert response.status_code == 200
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_provider_with_mock():
    """Test provider with mocked API call."""
    with patch('fiml.providers.yahoo.yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {"currentPrice": 150.0}
        
        provider = YahooFinanceProvider()
        price = await provider.fetch_price("AAPL")
        
        assert price == 150.0
```

### Parametrized Tests

Test multiple scenarios:

```python
@pytest.mark.parametrize("symbol,expected_valid", [
    ("AAPL", True),
    ("GOOGL", True),
    ("INVALID", False),
])
def test_symbol_validation(symbol, expected_valid):
    """Test symbol validation."""
    is_valid = validate_symbol(symbol)
    assert is_valid == expected_valid
```

## Test Configuration

### pytest.ini Options

Configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "live: marks tests as requiring live system",
    "slow: marks tests as slow",
]
```

### Environment Variables

Set test-specific variables:

```bash
# .env.test
ENVIRONMENT=test
LOG_LEVEL=DEBUG
CACHE_ENABLED=false
POSTGRES_DB=fiml_test
```

## CI/CD Testing

Tests run automatically on:
- Pull requests
- Pushes to main
- Nightly builds

See [CI workflow](https://github.com/kiarashplusplus/FIML/blob/main/.github/workflows/ci.yml).

## Coverage Goals

- **Overall**: 80%+
- **Core components**: 90%+
- **Providers**: 70%+
- **API endpoints**: 85%+

Current coverage: **67%**

## Test Data

### Fixtures

Use realistic test data:

```python
@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    return {
        "symbol": "AAPL",
        "price": 150.25,
        "timestamp": "2025-11-23T10:00:00Z",
        "provider": "yahoo"
    }
```

### Factories

Use factories for complex objects:

```python
from factory import Factory, Faker

class PriceDataFactory(Factory):
    class Meta:
        model = PriceData
    
    symbol = Faker('stock_symbol')
    price = Faker('pyfloat', min_value=1, max_value=1000)
    timestamp = Faker('date_time')
```

## Debugging Tests

### Run with Debug Output

```bash
pytest tests/ -v -s
```

### Run with PDB

```bash
pytest tests/ --pdb
```

Drop into debugger on failure:

```bash
pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### Verbose Logging

```bash
pytest tests/ -v --log-cli-level=DEBUG
```

## Common Issues

### Async Tests Hanging

Make sure to use `pytest-asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Database Connection Errors

Ensure test database is running:

```bash
docker-compose up -d postgres
pytest tests/test_database.py
```

### Cache Conflicts

Clean Redis before tests:

```bash
docker-compose exec redis redis-cli FLUSHALL
pytest tests/test_cache.py
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Names**: Descriptive test function names
3. **Single Assertion**: Test one thing at a time
4. **Fast Tests**: Mock external dependencies
5. **Readable**: Use clear arrange/act/assert structure
6. **Maintain**: Update tests with code changes

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Test Coverage](https://github.com/kiarashplusplus/FIML/blob/main/TEST_REPORT.md)

## Next Steps

- Review [Test Report](https://github.com/kiarashplusplus/FIML/blob/main/TEST_REPORT.md)
- Check [CI/CD Pipeline](https://github.com/kiarashplusplus/FIML/actions)
- Read [Contributing Guide](contributing.md)
