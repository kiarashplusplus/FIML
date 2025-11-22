.PHONY: help install dev build up down logs test lint format clean

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
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	pytest -v --cov=fiml --cov-report=html --cov-report=term

lint:
	ruff check fiml/
	mypy fiml/

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
	docker-compose exec fiml-server /bin/bash

migrate:
	docker-compose exec fiml-server python -m fiml.db.migrate

psql:
	docker-compose exec postgres psql -U fiml -d fiml

redis-cli:
	docker-compose exec redis redis-cli

ray-dashboard:
	@echo "Ray Dashboard: http://localhost:8265"

grafana:
	@echo "Grafana: http://localhost:3000 (admin/admin)"

prometheus:
	@echo "Prometheus: http://localhost:9090"

restart:
	docker-compose restart fiml-server

rebuild:
	docker-compose up -d --build fiml-server
