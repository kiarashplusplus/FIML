.PHONY: help install dev build up down logs test lint format clean benchmark

help:
	@echo "FIML - Financial Intelligence Meta-Layer"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      Install production dependencies"
	@echo "  make dev          Install development dependencies"
	@echo "  make build        Build Docker images"
	@echo "  make up           Start all services"
	@echo "  make down         Stop all services"
	@echo "  make logs         View logs"
	@echo "  make test         Run tests"
	@echo "  make benchmark    Run performance benchmarks"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo "  make clean        Clean build artifacts"
	@echo "  make shell        Open shell in container"
	@echo "  make migrate      Run database migrations"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	pytest -v --cov=fiml --cov-report=html --cov-report=term

benchmark:
	pytest benchmarks/ --benchmark-only --benchmark-verbose

benchmark-save:
	pytest benchmarks/ --benchmark-only --benchmark-autosave

benchmark-compare:
	pytest benchmarks/ --benchmark-only --benchmark-compare

# Performance Testing
install-perf:
	pip install -e ".[dev,performance]"

test-performance:
	@echo "Running performance target tests..."
	pytest tests/performance/test_targets.py -v

test-performance-full:
	@echo "Running full performance test suite..."
	pytest tests/performance/stress_test.py -v -m slow
	pytest tests/performance/test_targets.py -v

test-load:
	@echo "Starting load test (use Ctrl+C to stop)..."
	locust -f tests/performance/load_test.py --host=http://localhost:8000

test-load-headless:
	@echo "Running headless load test (100 users, 5 minutes)..."
	locust -f tests/performance/load_test.py \
		--host=http://localhost:8000 \
		--users 100 \
		--spawn-rate 10 \
		--run-time 5m \
		--headless \
		--html tests/performance/reports/load_test_report.html

profile-cache:
	@echo "Profiling cache operations..."
	python tests/performance/profile.py --target cache --duration 30

profile-providers:
	@echo "Profiling provider fetches..."
	python tests/performance/profile.py --target providers --duration 30

perf-baseline:
	@echo "Creating performance baseline..."
	python tests/performance/regression_detection.py --save-baseline

perf-compare:
	@echo "Comparing performance with baseline..."
	python tests/performance/regression_detection.py \
		--baseline benchmark_baseline.json \
		--report regression_report.txt

perf-report:
	@echo "Generating performance report..."
	python tests/performance/generate_report.py --output PERFORMANCE_REPORT.md
	@echo "Report saved to PERFORMANCE_REPORT.md"

lint:
	ruff check fiml/
	mypy fiml/core/ fiml/cache/

format:
	black fiml/ tests/
	isort fiml/ tests/
	ruff check --fix fiml/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

shell:
	docker compose exec fiml-server /bin/bash

migrate:
	docker compose exec fiml-server python -m fiml.db.migrate

psql:
	docker compose exec postgres psql -U fiml -d fiml

redis-cli:
	docker compose exec redis redis-cli

ray-dashboard:
	@echo "Ray Dashboard: http://localhost:8265"

grafana:
	@echo "Grafana: http://localhost:3000 (admin/admin)"

prometheus:
	@echo "Prometheus: http://localhost:9090"

restart:
	docker compose restart fiml-server

rebuild:
	docker compose up -d --build fiml-server
