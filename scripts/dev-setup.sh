#!/usr/bin/env bash
set -e

echo "🚀 Starting FIML Development Environment"

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example"
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys before continuing"
    exit 0
fi

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

# Run database migrations
echo "📊 Running database migrations..."
docker-compose exec -T postgres psql -U fiml -d fiml -f /docker-entrypoint-initdb.d/init.sql || true

echo "✅ FIML is ready!"
echo ""
echo "📍 Service URLs:"
echo "   - API:        http://localhost:8000"
echo "   - API Docs:   http://localhost:8000/docs"
echo "   - Health:     http://localhost:8000/health"
echo "   - Grafana:    http://localhost:3000 (admin/admin)"
echo "   - Prometheus: http://localhost:9090"
echo "   - Ray:        http://localhost:8265"
echo ""
echo "📖 View logs:     make logs"
echo "🛑 Stop services: make down"
