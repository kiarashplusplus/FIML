"""
Tests for Core modules - models, config, exceptions, logging, sentry
"""

from unittest.mock import MagicMock, patch

from fiml.core.config import Settings
from fiml.core.exceptions import (
    ArbitrationError,
    CacheError,
    ComplianceError,
    DataQualityError,
    FIMLException,
    FKDSLExecutionError,
    FKDSLParseError,
    NoProviderAvailableError,
    ProviderError,
)
from fiml.core.logging import get_logger
from fiml.core.models import (
    ArbitrationPlan,
    Asset,
    AssetType,
    DataLineage,
    Market,
    ProviderScore,
    TaskInfo,
    TaskStatus,
)
from fiml.core.sentry import (
    add_breadcrumb,
    capture_exception,
    capture_message,
    init_sentry,
    set_context,
    set_tag,
    set_user,
)


class TestModels:
    """Test core models"""

    def test_asset_creation(self):
        """Test creating an asset"""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.EQUITY,
            market=Market.US,
            exchange="NASDAQ",
            currency="USD",
        )
        assert asset.symbol == "AAPL"
        assert asset.asset_type == AssetType.EQUITY
        assert asset.market == Market.US

    def test_asset_symbol_validation(self):
        """Test asset symbol validation"""
        asset = Asset(symbol="  aapl  ", asset_type=AssetType.EQUITY, market=Market.US)
        assert asset.symbol == "AAPL"  # Should be uppercase and trimmed

    def test_provider_score(self):
        """Test provider score model"""
        score = ProviderScore(
            total=85.5,
            freshness=90.0,
            latency=80.0,
            uptime=95.0,
            completeness=85.0,
            reliability=88.0,
        )
        assert score.total == 85.5
        assert score.freshness == 90.0

    def test_data_lineage(self):
        """Test data lineage model"""
        lineage = DataLineage(
            providers=["yahoo_finance", "mock_provider"],
            arbitration_score=0.95,
            conflict_resolved=True,
            source_count=2,
        )
        assert len(lineage.providers) == 2
        assert lineage.conflict_resolved is True

    def test_task_info(self):
        """Test task info model"""
        task = TaskInfo(
            id="task-123",
            type="fetch_price",
            status=TaskStatus.PENDING,
            resource_url="/api/tasks/task-123",
            progress=0.0,
        )
        assert task.id == "task-123"
        assert task.status == TaskStatus.PENDING

    def test_arbitration_plan(self):
        """Test arbitration plan model"""
        plan = ArbitrationPlan(
            primary_provider="yahoo_finance",
            fallback_providers=["mock_provider"],
            estimated_latency_ms=100,
            timeout_ms=5000,
        )
        assert plan.primary_provider == "yahoo_finance"
        assert len(plan.fallback_providers) == 1


class TestConfig:
    """Test configuration"""

    def test_settings_creation(self):
        """Test creating settings"""
        settings = Settings(
            fiml_env="development", redis_host="localhost", postgres_host="localhost"
        )
        assert settings.fiml_env == "development"
        assert settings.redis_host == "localhost"


class TestExceptions:
    """Test custom exceptions"""

    def test_fiml_error(self):
        """Test base FIML error"""
        error = FIMLException("Test error")
        assert str(error) == "Test error"

    def test_provider_error(self):
        """Test provider error"""
        error = ProviderError("Provider failed")
        assert str(error) == "Provider failed"

    def test_no_provider_available_error(self):
        """Test no provider available error"""
        error = NoProviderAvailableError("No providers for AAPL")
        assert "No providers for AAPL" in str(error)

    def test_data_quality_error(self):
        """Test data quality error"""
        error = DataQualityError("Invalid data")
        assert str(error) == "Invalid data"

    def test_arbitration_error(self):
        """Test arbitration error"""
        error = ArbitrationError("Arbitration failed")
        assert str(error) == "Arbitration failed"

    def test_fkdsl_parse_error(self):
        """Test FK-DSL parse error"""
        error = FKDSLParseError("Parse failed")
        assert str(error) == "Parse failed"

    def test_fkdsl_execution_error(self):
        """Test FK-DSL execution error"""
        error = FKDSLExecutionError("Execution failed")
        assert str(error) == "Execution failed"

    def test_cache_error(self):
        """Test cache error"""
        error = CacheError("Cache failed")
        assert str(error) == "Cache failed"

    def test_compliance_error(self):
        """Test compliance error"""
        error = ComplianceError("Compliance check failed")
        assert str(error) == "Compliance check failed"


class TestLogging:
    """Test logging"""

    def test_get_logger(self):
        """Test getting a logger"""
        logger = get_logger("test_module")
        assert logger is not None

        # Test logging methods exist
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")


class TestSentry:
    """Test Sentry integration"""

    def test_init_sentry_without_dsn(self):
        """Test that Sentry is not initialized when DSN is None or empty"""
        assert init_sentry(dsn=None) is False
        assert init_sentry(dsn="") is False

    @patch("fiml.core.sentry.sentry_sdk.init")
    def test_init_sentry_with_dsn(self, mock_init):
        """Test that Sentry is initialized when DSN is provided"""
        mock_init.return_value = None
        result = init_sentry(
            dsn="https://test@sentry.io/123",
            environment="test",
            release="fiml@1.0.0",
        )
        assert result is True
        mock_init.assert_called_once()

    @patch("fiml.core.sentry.sentry_sdk.init")
    def test_init_sentry_handles_exception(self, mock_init):
        """Test that Sentry initialization failure doesn't crash the app"""
        mock_init.side_effect = Exception("Initialization failed")
        result = init_sentry(dsn="https://test@sentry.io/123")
        assert result is False

    @patch("fiml.core.sentry.sentry_sdk.capture_exception")
    @patch("fiml.core.sentry.sentry_sdk.push_scope")
    def test_capture_exception(self, mock_push_scope, mock_capture):
        """Test capturing an exception"""
        mock_scope = MagicMock()
        mock_push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_push_scope.return_value.__exit__ = MagicMock(return_value=False)
        mock_capture.return_value = "event-123"

        exc = ValueError("Test exception")
        result = capture_exception(exc, custom_key="custom_value")

        assert result == "event-123"
        mock_scope.set_extra.assert_called_with("custom_key", "custom_value")
        mock_capture.assert_called_once_with(exc)

    @patch("fiml.core.sentry.sentry_sdk.capture_message")
    @patch("fiml.core.sentry.sentry_sdk.push_scope")
    def test_capture_message(self, mock_push_scope, mock_capture):
        """Test capturing a message"""
        mock_scope = MagicMock()
        mock_push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_push_scope.return_value.__exit__ = MagicMock(return_value=False)
        mock_capture.return_value = "event-456"

        result = capture_message("Test message", level="warning", extra="data")

        assert result == "event-456"
        mock_scope.set_extra.assert_called_with("extra", "data")
        mock_capture.assert_called_once_with("Test message", level="warning")

    @patch("fiml.core.sentry.sentry_sdk.set_user")
    def test_set_user(self, mock_set_user):
        """Test setting user context"""
        set_user(user_id="user-123", email="test@example.com")
        mock_set_user.assert_called_once_with({"id": "user-123", "email": "test@example.com"})

    @patch("fiml.core.sentry.sentry_sdk.set_user")
    def test_set_user_without_id(self, mock_set_user):
        """Test setting user context without ID"""
        set_user(email="test@example.com")
        mock_set_user.assert_called_once_with({"email": "test@example.com"})

    @patch("fiml.core.sentry.sentry_sdk.set_user")
    def test_set_user_clear(self, mock_set_user):
        """Test clearing user context"""
        set_user()
        mock_set_user.assert_called_once_with(None)

    @patch("fiml.core.sentry.sentry_sdk.set_tag")
    def test_set_tag(self, mock_set_tag):
        """Test setting a tag"""
        set_tag("provider", "yahoo_finance")
        mock_set_tag.assert_called_once_with("provider", "yahoo_finance")

    @patch("fiml.core.sentry.sentry_sdk.set_context")
    def test_set_context(self, mock_set_context):
        """Test setting context"""
        context = {"asset": "AAPL", "market": "US"}
        set_context("trade", context)
        mock_set_context.assert_called_once_with("trade", context)

    @patch("fiml.core.sentry.sentry_sdk.add_breadcrumb")
    def test_add_breadcrumb(self, mock_add_breadcrumb):
        """Test adding a breadcrumb"""
        add_breadcrumb(
            message="User clicked button",
            category="user",
            level="info",
            data={"button": "submit"},
        )
        mock_add_breadcrumb.assert_called_once_with(
            message="User clicked button",
            category="user",
            level="info",
            data={"button": "submit"},
        )

    @patch("fiml.core.sentry.sentry_sdk.add_breadcrumb")
    def test_add_breadcrumb_defaults(self, mock_add_breadcrumb):
        """Test adding a breadcrumb with defaults"""
        add_breadcrumb(message="Simple message")
        mock_add_breadcrumb.assert_called_once_with(
            message="Simple message",
            category="default",
            level="info",
            data={},
        )
