# Testing with Automatic Test Infrastructure

This project automatically provisions Redis and PostgreSQL for testing using Docker.

## Quick Start

### Run All Tests
```bash
pytest tests/
```

That's it! Docker containers will start automatically.

## Test Output Example
```
🐳 Starting test containers (Redis & PostgreSQL)...
⏳ Waiting for Redis to be ready...
✅ Redis is ready
⏳ Waiting for PostgreSQL to be ready...
✅ PostgreSQL is ready
✅ All test services are ready

tests/test_cache.py::TestL1Cache::test_l1_cache_lifecycle PASSED
tests/test_cache.py::TestL2Cache::test_l2_cache_initialization PASSED
...

🧹 Cleaning up test containers...
✅ Test containers cleaned up
```

## Prerequisites
- Docker installed and running
- Python dependencies installed: `pip install -e ".[dev]"`

## Options

### Use Existing Services (Skip Docker)
If you already have Redis and PostgreSQL running:
```bash
pytest tests/ --no-docker
```

Requirements when using `--no-docker`:
- Redis on `localhost:6379`
- PostgreSQL on `localhost:5432`
  - Database: `fiml_test`
  - User: `fiml_test`
  - Password: `fiml_test_password`

### Run Specific Test Files
```bash
pytest tests/test_cache.py -v
pytest tests/test_integration.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=fiml --cov-report=html
```

## Test Infrastructure

### Services
- **Redis 7 Alpine**: L1 cache testing
- **PostgreSQL 16 Alpine**: L2 cache testing

### Configuration
- Test containers defined in `docker-compose.test.yml`
- Pytest fixtures in `tests/conftest.py`
- Environment variables automatically set for test databases

### Cleanup
Containers are automatically removed after tests complete. If interrupted:
```bash
docker-compose -f docker-compose.test.yml down -v
```

## Troubleshooting

### Docker not available
```
Error: Docker is not available. Install Docker or use --no-docker flag.
```
**Solution**: Install Docker or use `--no-docker` with manual services

### Services failed to start
```
Error: Redis failed to start within timeout period
```
**Solution**: 
1. Check Docker is running: `docker ps`
2. Check ports aren't in use: `lsof -i :6379 -i :5432`
3. Clean up old containers: `docker-compose -f docker-compose.test.yml down -v`

### Tests still skip
If you see skipped tests, check the reason:
```bash
pytest tests/ -v -ra  # Shows skip reasons
```

Valid skip reasons:
- Ray cluster not available (multi-agent tests)
- External API keys not configured (live system tests)
- Market data providers not available (websocket tests)

These are expected and unrelated to Redis/PostgreSQL infrastructure.

## Test Statistics

- **Total Tests**: 267
- **Passing**: 260
- **Skipped**: 5 (Ray/Live system, not Redis/PostgreSQL)
- **Infrastructure-dependent**: 0 (all automated!)
