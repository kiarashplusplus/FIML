# Quick Start: Running Tests

## TL;DR
```bash
pytest tests/
```

That's it! Redis and PostgreSQL will start automatically in Docker containers.

## What You'll See
```
🐳 Starting test containers (Redis & PostgreSQL)...
⏳ Waiting for Redis to be ready...
✅ Redis is ready
⏳ Waiting for PostgreSQL to be ready...
✅ PostgreSQL is ready
✅ All test services are ready

tests/test_cache.py ...................... [ 10%]
tests/test_integration.py ................ [ 20%]
...
260 passed, 5 skipped in 75.76s

🧹 Cleaning up test containers...
✅ Test containers cleaned up
```

## Requirements
- Docker (must be running)
- Python 3.11+
- Dependencies: `pip install -e ".[dev]"`

## Common Commands

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_cache.py -v
```

### Run with coverage
```bash
pytest tests/ --cov=fiml
```

### Skip Docker (use existing services)
```bash
pytest tests/ --no-docker
```

## What Changed?
**Before**: 24 tests skipped (Redis/PostgreSQL not available)  
**After**: 0 tests skipped for Redis/PostgreSQL - containers auto-start!

## Need Help?
See `docs/TESTING.md` for full documentation.
