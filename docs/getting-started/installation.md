# Installation

This guide will help you install and set up FIML on your local machine or server.

## Prerequisites

Before installing FIML, ensure you have the following:

- **Docker & Docker Compose** (recommended for easiest setup)
- **Python 3.11+** (for development setup)
- **API keys** for data providers (Alpha Vantage, FMP, etc.)

## One-Command Installation (Recommended)

The quickest way to get started with FIML is using our interactive quickstart script:

```bash
git clone https://github.com/kiarashplusplus/FIML.git
cd FIML
./quickstart.sh
```

This script will:

1. ✅ Check prerequisites
2. ✅ Setup environment variables
3. ✅ Build Docker images
4. ✅ Start all services
5. ✅ Initialize database
6. ✅ Verify health

## Manual Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/kiarashplusplus/FIML.git
cd FIML
```

### Step 2: Configure Environment

Copy the example environment file and edit it with your configuration:

```bash
cp .env.example .env
```

Edit `.env` with your preferred text editor and add your API keys:

```bash
# Data Provider API Keys
ALPHA_VANTAGE_API_KEY=your_key_here
FMP_API_KEY=your_key_here
CCXT_API_KEY=your_key_here

# Database Configuration
POSTGRES_USER=fiml
POSTGRES_PASSWORD=fiml_password
POSTGRES_DB=fiml

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### Step 3: Start Services with Docker Compose

Build and start all services:

```bash
make build
make up
```

Or using docker-compose directly:

```bash
docker-compose up -d
```

### Step 4: Verify Installation

Check that all services are running:

```bash
curl http://localhost:8000/health
```

You should see a response like:

```json
{
  "status": "healthy",
  "version": "0.3.0",
  "services": {
    "api": "running",
    "redis": "connected",
    "postgres": "connected"
  }
}
```

## Development Setup

For local development without Docker:

### Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
# Install development dependencies
make dev

# Or using pip directly
pip install -e ".[dev]"
```

### Run Tests

```bash
make test

# Or run specific tests
pytest tests/test_arbitration.py -v
```

### Format Code

```bash
make format

# Or run formatters directly
black fiml tests
ruff check --fix fiml tests
```

## Service Ports

Once installed, the following services will be available:

| Service | Port | URL |
|---------|------|-----|
| API Server | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Prometheus | 9091 | http://localhost:9091 |
| Grafana | 3000 | http://localhost:3000 |
| Ray Dashboard | 8265 | http://localhost:8265 |

## Troubleshooting

### Docker Build Fails

If you encounter build errors:

```bash
# Clean up old containers and images
docker-compose down -v
docker system prune -f

# Rebuild from scratch
docker-compose build --no-cache
```

### Port Already in Use

If port 8000 is already in use, you can change it in `.env`:

```bash
SERVER_PORT=8001
```

### API Key Issues

Make sure your API keys are valid and have the necessary permissions. Test them individually:

```bash
# Test Alpha Vantage
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=YOUR_KEY"
```

### Database Connection Issues

If you can't connect to the database:

```bash
# Check if PostgreSQL container is running
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Learn how to use FIML
- [Configuration Guide](configuration.md) - Advanced configuration options
- [API Documentation](../api/rest.md) - Explore the API

## Getting Help

If you encounter issues:

- Check our [GitHub Issues](https://github.com/kiarashplusplus/FIML/issues)
- Join our [Discord community](https://discord.gg/fiml)
- Read the [FAQ](../user-guide/overview.md#faq)
