#!/usr/bin/env bash
# FIML Quick Start Script

cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███████╗██╗███╗   ██╗ █████╗ ███╗   ██╗ ██████╗███████╗║
║   ██╔════╝██║████╗  ██║██╔══██╗████╗  ██║██╔════╝██╔════╝║
║   █████╗  ██║██╔██╗ ██║███████║██╔██╗ ██║██║     █████╗  ║
║   ██╔══╝  ██║██║╚██╗██║██╔══██║██║╚██╗██║██║     ██╔══╝  ║
║   ██║     ██║██║ ╚████║██║  ██║██║ ╚████║╚██████╗███████╗║
║   ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝║
║                                                           ║
║        Financial Intelligence Meta-Layer v0.1.0          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

echo "🚀 Welcome to FIML Setup!"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."
echo ""

MISSING_DEPS=()

if ! command_exists docker; then
    MISSING_DEPS+=("docker")
fi

if ! command_exists docker-compose; then
    MISSING_DEPS+=("docker-compose")
fi

if ! command_exists python3; then
    MISSING_DEPS+=("python3")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "❌ Missing dependencies:"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "   - $dep"
    done
    echo ""
    echo "Please install missing dependencies and try again."
    exit 1
fi

echo "✅ All prerequisites met!"
echo ""

# Check .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env with your API keys:"
    echo "   - ALPHA_VANTAGE_API_KEY"
    echo "   - FMP_API_KEY"
    echo "   - Other provider keys as needed"
    echo ""
    read -p "Press Enter after you've configured .env (or continue with defaults for testing)..."
fi

# Offer installation options
echo ""
echo "Choose installation method:"
echo "1) Docker Compose (Recommended - Full stack)"
echo "2) Python Virtual Environment (Development only)"
echo "3) Both"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1|3)
        echo ""
        echo "🐳 Starting Docker Compose setup..."
        echo ""
        
        # Build images
        echo "🏗️  Building Docker images..."
        docker-compose build
        
        # Start services
        echo "🚀 Starting services..."
        docker-compose up -d
        
        # Wait for services
        echo "⏳ Waiting for services to be ready..."
        sleep 15
        
        # Initialize database
        echo "📊 Initializing database..."
        docker-compose exec -T postgres psql -U fiml -d fiml -f /docker-entrypoint-initdb.d/init.sql 2>/dev/null || true
        
        # Check health
        echo ""
        echo "🏥 Checking service health..."
        if curl -s http://localhost:8000/health > /dev/null; then
            echo "✅ FIML server is healthy!"
        else
            echo "⚠️  FIML server may not be ready yet. Check logs with: make logs"
        fi
        
        echo ""
        echo "✅ Docker setup complete!"
        ;;
esac

case $choice in
    2|3)
        echo ""
        echo "🐍 Setting up Python virtual environment..."
        
        # Create venv
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        
        # Activate venv
        source venv/bin/activate
        
        # Install dependencies
        echo "📦 Installing dependencies..."
        pip install --upgrade pip setuptools wheel
        pip install -e ".[dev]"
        
        echo ""
        echo "✅ Python environment ready!"
        echo "   Activate with: source venv/bin/activate"
        ;;
esac

# Display summary
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                 🎉 FIML Setup Complete! 🎉                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Service URLs:"
echo "   • API Server:    http://localhost:8000"
echo "   • API Docs:      http://localhost:8000/docs"
echo "   • Health Check:  http://localhost:8000/health"
echo "   • Grafana:       http://localhost:3000 (admin/admin)"
echo "   • Prometheus:    http://localhost:9090"
echo "   • Ray Dashboard: http://localhost:8265"
echo ""
echo "📖 Useful Commands:"
echo "   • View logs:      make logs"
echo "   • Run tests:      make test"
echo "   • Stop services:  make down"
echo "   • Format code:    make format"
echo "   • Shell access:   make shell"
echo ""
echo "🎯 Try the examples:"
echo "   python examples/basic_usage.py"
echo ""
echo "📚 Documentation:"
echo "   • README.md         - Getting started"
echo "   • ARCHITECTURE.md   - System design"
echo "   • DEPLOYMENT.md     - Production deployment"
echo "   • BUILD_SUMMARY.md  - Current status & roadmap"
echo ""
echo "🤝 Need help?"
echo "   • GitHub Issues: https://github.com/your-org/fiml/issues"
echo "   • Documentation: https://docs.fiml.ai"
echo ""
echo "⚠️  Disclaimer: FIML provides financial data for informational"
echo "   purposes only. Not financial advice. DYOR!"
echo ""
