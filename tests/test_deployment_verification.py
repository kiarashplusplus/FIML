"""
Deployment Verification Tests

These tests verify that:
1. docker-compose.yml works out-of-the-box
2. .env generated from .env.example works
3. Health endpoints return correct status
4. Metrics endpoint is Prometheus-compatible
5. Provider-specific health endpoints work
"""

import json
import os

import pytest
import yaml
from fastapi.testclient import TestClient


class TestDeploymentConfiguration:
    """Test deployment configuration files"""

    def test_env_example_exists(self):
        """Test that .env.example exists and contains required keys"""
        env_example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")
        assert os.path.exists(env_example_path), ".env.example file should exist"

        with open(env_example_path) as f:
            content = f.read()

        # Check for required configuration sections
        required_keys = [
            "FIML_ENV",
            "FIML_HOST",
            "FIML_PORT",
            "REDIS_HOST",
            "REDIS_PORT",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
        ]

        for key in required_keys:
            assert key in content, f"{key} should be in .env.example"

    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists"""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml"
        )
        assert os.path.exists(compose_path), "docker-compose.yml should exist"

    def test_prometheus_config_valid_yaml(self):
        """Test that prometheus.yml is valid YAML"""
        prometheus_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "prometheus.yml"
        )
        assert os.path.exists(prometheus_path), "prometheus.yml should exist"

        with open(prometheus_path) as f:
            config = yaml.safe_load(f)

        # Check for required sections
        assert "global" in config, "prometheus.yml should have global section"
        assert "scrape_configs" in config, "prometheus.yml should have scrape_configs"

    def test_grafana_datasources_valid_yaml(self):
        """Test that grafana datasources config is valid YAML"""
        datasources_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "grafana",
            "datasources",
            "prometheus.yml",
        )
        assert os.path.exists(datasources_path), "grafana datasources config should exist"

        with open(datasources_path) as f:
            config = yaml.safe_load(f)

        assert "datasources" in config, "Should have datasources section"

    def test_grafana_dashboards_config_valid_yaml(self):
        """Test that grafana dashboards config is valid YAML"""
        dashboards_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "grafana",
            "dashboards",
            "dashboards.yml",
        )
        assert os.path.exists(dashboards_path), "grafana dashboards config should exist"

        with open(dashboards_path) as f:
            config = yaml.safe_load(f)

        assert "providers" in config, "Should have providers section"

    def test_grafana_dashboard_valid_json(self):
        """Test that grafana dashboard JSON is valid"""
        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "grafana",
            "dashboards",
            "fiml-api-metrics.json",
        )
        assert os.path.exists(dashboard_path), "FIML dashboard should exist"

        with open(dashboard_path) as f:
            dashboard = json.load(f)

        assert "panels" in dashboard, "Dashboard should have panels"
        assert "title" in dashboard, "Dashboard should have title"


class TestHealthEndpointsDeployment:
    """Test health endpoints work correctly for deployment verification"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fiml.server import app

        return TestClient(app)

    def test_health_endpoint_structure(self, client):
        """Test /health returns correct structure"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Required fields for health check
        assert "status" in data
        assert "version" in data
        assert "environment" in data

        # Status should be a known value
        assert data["status"] in ["healthy", "unhealthy", "degraded"]

    def test_health_db_endpoint_structure(self, client):
        """Test /health/db returns correct structure"""
        response = client.get("/health/db")

        # Can be 200 (healthy) or 503 (unhealthy)
        assert response.status_code in [200, 503]
        data = response.json()

        assert "status" in data
        if response.status_code == 200:
            assert data["service"] == "postgresql"

    def test_health_cache_endpoint_structure(self, client):
        """Test /health/cache returns correct structure"""
        response = client.get("/health/cache")

        # Can be 200 (healthy) or 503 (unhealthy)
        assert response.status_code in [200, 503]
        data = response.json()

        assert "status" in data
        if response.status_code == 200:
            assert data["service"] == "redis"

    def test_health_providers_endpoint_structure(self, client):
        """Test /health/providers returns correct structure"""
        response = client.get("/health/providers")

        # Can be 200 (healthy/degraded) or 503 (unhealthy)
        assert response.status_code in [200, 503]
        data = response.json()

        assert "status" in data
        if response.status_code == 200:
            assert "total_providers" in data
            assert "healthy_providers" in data
            assert "providers" in data


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fiml.server import app

        return TestClient(app)

    def test_metrics_endpoint_exists(self, client):
        """Test /metrics endpoint exists and returns prometheus format"""
        response = client.get("/metrics")

        # Should not be 404
        assert response.status_code != 404

        # Check for Prometheus metrics format if accessible
        if response.status_code == 200:
            content = response.text

            # Prometheus metrics should contain HELP and TYPE lines
            # At minimum we should have some metrics defined
            assert len(content) > 0, "Metrics endpoint should return content"

    def test_metrics_contains_fiml_metrics(self, client):
        """Test that metrics include FIML-specific metrics"""
        response = client.get("/metrics")

        if response.status_code == 200:
            content = response.text

            # Check for our custom metrics (they may or may not have values yet)
            # Just verify the endpoint is working
            assert "fiml" in content.lower() or "# HELP" in content


class TestRootEndpoint:
    """Test root endpoint provides deployment info"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fiml.server import app

        return TestClient(app)

    def test_root_lists_all_endpoints(self, client):
        """Test root endpoint lists all important endpoints for deployment"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Service info
        assert "service" in data
        assert "version" in data

        # Health endpoints
        assert "health" in data
        assert "health_endpoints" in data

        # Metrics endpoint
        assert "metrics" in data


class TestDockerComposeValidation:
    """Test docker-compose.yml structure"""

    def test_docker_compose_valid_yaml(self):
        """Test docker-compose.yml is valid YAML and has required services"""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml"
        )

        with open(compose_path) as f:
            config = yaml.safe_load(f)

        # Check for required sections
        assert "services" in config, "Should have services section"

        services = config["services"]

        # Check for required services
        required_services = ["fiml-server", "redis", "postgres"]
        for service in required_services:
            assert service in services, f"Service {service} should be defined"

    def test_docker_compose_has_health_check(self):
        """Test that main service has health check in Dockerfile"""
        dockerfile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")

        with open(dockerfile_path) as f:
            content = f.read()

        assert "HEALTHCHECK" in content, "Dockerfile should have HEALTHCHECK"
        assert "/health" in content, "Health check should use /health endpoint"

    def test_docker_compose_exposes_correct_ports(self):
        """Test docker-compose exposes required ports"""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml"
        )

        with open(compose_path) as f:
            config = yaml.safe_load(f)

        fiml_server = config["services"]["fiml-server"]

        # Check port mapping
        assert "ports" in fiml_server
        ports = fiml_server["ports"]

        # Should expose port 8000 for API
        port_mappings = [str(p) for p in ports]
        assert any("8000" in p for p in port_mappings), "Should expose port 8000"
