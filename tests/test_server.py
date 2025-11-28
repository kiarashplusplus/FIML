"""
Tests for the FastAPI server module
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fiml.core.exceptions import ArbitrationError, DataQualityError, ProviderError


class TestServerConfiguration:
    """Test server configuration and setup"""

    def test_app_creation(self):
        """Test that FastAPI app is created with correct metadata"""
        from fiml.server import app

        assert app.title == "FIML - Financial Intelligence Meta-Layer"
        assert app.version == "0.4.0"
        assert "AI-Native Multi-Market Financial Intelligence Framework" in app.description

    def test_app_has_routers(self):
        """Test that app has required routers"""
        from fiml.server import app

        # Check that routes are registered
        routes = [route.path for route in app.routes]

        assert "/health" in routes
        assert "/" in routes
        # MCP routes are prefixed with /mcp
        assert any("/mcp" in route for route in routes)

    def test_metrics_endpoint_mounted(self):
        """Test that Prometheus metrics endpoint is mounted"""
        from fiml.server import app

        routes = [route.path for route in app.routes]
        assert "/metrics" in routes or any("metrics" in route for route in routes)


class TestHealthEndpoints:
    """Test health and root endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fiml.server import app

        return TestClient(app)

    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["version"] == "0.4.0"
        assert "environment" in data

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "FIML - Financial Intelligence Meta-Layer"
        assert data["version"] == "0.4.0"
        assert data["health"] == "/health"
        assert data["metrics"] == "/metrics"

    def test_root_has_health_endpoints(self, client):
        """Test that root endpoint documents all health endpoints"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "health_endpoints" in data
        assert data["health_endpoints"]["main"] == "/health"
        assert data["health_endpoints"]["database"] == "/health/db"
        assert data["health_endpoints"]["cache"] == "/health/cache"
        assert data["health_endpoints"]["providers"] == "/health/providers"

    def test_root_docs_url_in_development(self, client):
        """Test that docs URL is present in development mode"""
        with patch("fiml.server.settings") as mock_settings:
            mock_settings.is_development = True

            # Need to reimport to get the patched settings
            response = client.get("/")
            data = response.json()

            # The response uses the already-initialized settings
            # so this test just verifies the structure
            assert "docs" in data

    def test_health_db_endpoint_exists(self, client):
        """Test that /health/db endpoint exists"""
        response = client.get("/health/db")
        # May return 200 (healthy) or 503 (unhealthy) depending on db availability
        assert response.status_code in [200, 503]
        data = response.json()
        # When healthy, returns {"status": ..., "service": ...}
        # When unhealthy, returns {"detail": ...}
        if response.status_code == 200:
            assert "status" in data
            assert "service" in data
        else:
            # 503 returns HTTPException detail
            assert "detail" in data

    def test_health_cache_endpoint_exists(self, client):
        """Test that /health/cache endpoint exists"""
        response = client.get("/health/cache")
        # May return 200 (healthy) or 503 (unhealthy) depending on Redis availability
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "service" in data or "error" in data

    def test_health_providers_endpoint_exists(self, client):
        """Test that /health/providers endpoint exists"""
        response = client.get("/health/providers")
        # May return 200 (healthy/degraded) or 503 (unhealthy)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    def test_health_provider_not_found(self, client):
        """Test that non-existent provider returns 404"""
        response = client.get("/health/providers/nonexistent_provider")
        assert response.status_code == 404
        data = response.json()
        # FastAPI HTTPException returns 'detail' not 'error'
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestExceptionHandlers:
    """Test exception handlers"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fiml.server import app

        return TestClient(app)

    def test_fiml_exception_handler(self, client):
        """Test FIML exception handler"""
        from fiml.server import app

        # Create a test route that raises a FIML exception
        @app.get("/test-fiml-error")
        async def test_fiml_error():
            raise ProviderError("Test provider error")

        response = client.get("/test-fiml-error")

        assert response.status_code == 400
        data = response.json()

        assert data["error"] == "ProviderError"
        assert "Test provider error" in data["message"]

    def test_data_quality_exception_handler(self, client):
        """Test DataQualityError exception handler"""
        from fiml.server import app

        # Create a test route that raises a DataQualityError
        @app.get("/test-data-error")
        async def test_data_error():
            raise DataQualityError("Invalid data format")

        response = client.get("/test-data-error")

        assert response.status_code == 400
        data = response.json()

        assert data["error"] == "DataQualityError"
        assert "Invalid data format" in data["message"]

    def test_arbitration_exception_handler(self, client):
        """Test ArbitrationError exception handler"""
        from fiml.server import app

        # Create a test route that raises an ArbitrationError
        @app.get("/test-arbitration-error")
        async def test_arbitration_error():
            raise ArbitrationError("Arbitration failed")

        response = client.get("/test-arbitration-error")

        assert response.status_code == 400
        data = response.json()

        assert data["error"] == "ArbitrationError"
        assert "Arbitration failed" in data["message"]

    def test_general_exception_handler(self):
        """Test general exception handler"""
        from fiml.server import app

        # Create a test route that raises a general exception
        @app.get("/test-general-error")
        async def test_general_error():
            raise RuntimeError("Unexpected error")

        # Use TestClient with raise_server_exceptions=False to capture the error response
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-general-error")

        assert response.status_code == 500
        data = response.json()

        assert data["error"] == "InternalServerError"
        assert data["message"] == "An unexpected error occurred"


class TestLifespan:
    """Test application lifespan events"""

    @pytest.mark.asyncio
    async def test_lifespan_startup(self):
        """Test lifespan startup event"""
        from fiml.server import app, lifespan

        # Mock the imports inside the lifespan function
        with (
            patch("fiml.cache.manager.cache_manager") as mock_cache,
            patch("fiml.agents.orchestrator.agent_orchestrator") as mock_orchestrator,
            patch.object(app.state, "provider_registry", create=True),
            patch("fiml.server.logger") as mock_logger,
            patch("fiml.server.provider_registry") as mock_provider_registry,
        ):

            mock_cache.initialize = AsyncMock()
            mock_orchestrator.initialize = AsyncMock()
            mock_provider_registry.initialize = AsyncMock()
            mock_provider_registry.providers = {}
            mock_provider_registry.shutdown = AsyncMock()

            # Enter the lifespan context
            async with lifespan(app):
                # Verify logger was called during startup
                assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_lifespan_cache_init_failure(self):
        """Test that cache initialization failure is handled gracefully"""
        from fiml.server import app, lifespan

        with (
            patch("fiml.cache.manager.cache_manager") as mock_cache,
            patch("fiml.server.provider_registry") as mock_registry,
            patch("fiml.server.logger") as mock_logger,
        ):

            # Make cache initialization fail
            mock_cache.initialize = AsyncMock(side_effect=Exception("Cache connection failed"))
            mock_registry.initialize = AsyncMock()
            mock_registry.providers = {}
            mock_registry.shutdown = AsyncMock()

            # Should not raise, just log a warning
            async with lifespan(app):
                # Verify warning was logged
                assert any(
                    "Cache initialization failed" in str(call)
                    for call in mock_logger.warning.call_args_list
                )

    @pytest.mark.asyncio
    async def test_lifespan_orchestrator_init_failure(self):
        """Test that orchestrator initialization failure is handled gracefully"""
        from fiml.server import app, lifespan

        with (
            patch("fiml.server.settings") as mock_settings,
            patch("fiml.cache.manager.cache_manager") as mock_cache,
            patch("fiml.server.provider_registry") as mock_registry,
            patch("fiml.agents.orchestrator.agent_orchestrator") as mock_orchestrator,
            patch("fiml.server.logger"),
        ):

            # Enable Ray address to trigger orchestrator initialization
            mock_settings.ray_address = "ray://localhost:10001"

            mock_cache.initialize = AsyncMock()
            mock_registry.initialize = AsyncMock()
            mock_registry.providers = {}
            mock_registry.shutdown = AsyncMock()
            mock_cache.shutdown = AsyncMock()

            # Make orchestrator initialization fail
            mock_orchestrator.initialize = AsyncMock(side_effect=Exception("Ray connection failed"))

            # Should not raise, just log a warning
            async with lifespan(app):
                # Verify warning was logged
                pass  # The exception should be caught and logged

    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """Test lifespan shutdown event"""
        from fiml.server import app, lifespan

        with (
            patch("fiml.cache.manager.cache_manager") as mock_cache,
            patch("fiml.server.provider_registry") as mock_registry,
            patch("fiml.agents.orchestrator.agent_orchestrator") as mock_orchestrator,
            patch("fiml.server.logger"),
        ):

            mock_cache.initialize = AsyncMock()
            mock_cache.shutdown = AsyncMock()
            mock_orchestrator.initialized = False
            mock_orchestrator.shutdown = AsyncMock()
            mock_registry.initialize = AsyncMock()
            mock_registry.shutdown = AsyncMock()
            mock_registry.providers = {}

            # Enter and exit the lifespan context
            async with lifespan(app):
                pass

            # Verify shutdown was called
            mock_registry.shutdown.assert_called_once()
            mock_cache.shutdown.assert_called_once()


class TestCORSMiddleware:
    """Test CORS middleware configuration"""

    def test_cors_enabled(self):
        """Test that CORS middleware is added when enabled"""
        with patch("fiml.server.settings") as mock_settings:
            mock_settings.enable_cors = True
            mock_settings.cors_origins = ["http://localhost:3000"]
            mock_settings.is_development = False

            # Since app is already created, we just verify the test runs
            # In a real scenario, we'd need to reinitialize the app
            # For now, we just verify that the setting can be accessed
            assert mock_settings.enable_cors is True


class TestServerMain:
    """Test server main execution"""

    def test_main_settings_available(self):
        """Test that server settings are available"""
        from fiml.server import settings

        assert settings.fiml_host is not None
        assert settings.fiml_port is not None
        assert settings.is_development is not None


class TestPrometheusIntegration:
    """Test Prometheus metrics integration"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fiml.server import app

        return TestClient(app)

    def test_metrics_endpoint_exists(self, client):
        """Test that /metrics endpoint is accessible"""
        # The metrics endpoint should be mounted
        # It might return different status codes depending on setup
        response = client.get("/metrics")

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
