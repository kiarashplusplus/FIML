# FIML Scripts

This directory contains utility scripts for the FIML project.

## Testing Scripts

### `test_live_system.sh` ✨ NEW

Comprehensive live system integration tests:
- Tests all 12 running Docker services
- Validates API endpoints, health checks, MCP protocol
- Checks infrastructure (Redis, PostgreSQL, Kafka, Ray, Grafana, Prometheus)
- Verifies Celery task queue connectivity
- **22 automated tests** with colored output

**Usage:**
```bash
./scripts/test_live_system.sh
```

**Also available from root:**
```bash
./live_demo.sh          # Quick demo
./check_test_status.sh  # Pytest suite
```

## Git Hooks

### `pre-push-hook.sh`

Pre-push git hook that runs quality checks before each push:
- Ruff linting (required)
- MyPy type checking (optional)
- Test suite (optional if dependencies installed)

**Installation:**
```bash
./scripts/install-hooks.sh
```

**Manual installation:**
```bash
cp scripts/pre-push-hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

See [docs/PRE_PUSH_HOOK.md](../docs/PRE_PUSH_HOOK.md) for details.

### `install-hooks.sh`

Automated installer for git hooks. Handles:
- Checking prerequisites
- Backing up existing hooks
- Installing new hooks
- Setting proper permissions

## Database Scripts

### `setup_session_db.py`

Initialize session management database tables.

### `load_test_cache.py`

Populate cache with test data for development.

### `init-db.sql`

PostgreSQL database schema initialization script.

## Usage

All scripts should be run from the project root directory:

```bash
# Install git hooks
./scripts/install-hooks.sh

# Setup database
python scripts/setup_session_db.py
```
