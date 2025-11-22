"""
Tests for Core modules - models, config, exceptions, logging
"""

import pytest
from datetime import datetime
from fiml.core.models import (
    Asset, AssetType, Market, DataType, AnalysisDepth, TaskStatus,
    ProviderScore, DataLineage, CachedData, StructuralData, TaskInfo,
    ComplianceInfo, NarrativeSummary, SearchBySymbolResponse,
    SearchByCoinResponse, ArbitrationPlan, ProviderHealth
)
from fiml.core.config import Settings
from fiml.core.exceptions import (
    FIMLException, ProviderError, NoProviderAvailableError,
    DataQualityError, ArbitrationError, FKDSLParseError,
    FKDSLExecutionError, CacheError, ComplianceError
)
from fiml.core.logging import get_logger


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
            currency="USD"
        )
        assert asset.symbol == "AAPL"
        assert asset.asset_type == AssetType.EQUITY
        assert asset.market == Market.US

    def test_asset_symbol_validation(self):
        """Test asset symbol validation"""
        asset = Asset(
            symbol="  aapl  ",
            asset_type=AssetType.EQUITY,
            market=Market.US
        )
        assert asset.symbol == "AAPL"  # Should be uppercase and trimmed

    def test_provider_score(self):
        """Test provider score model"""
        score = ProviderScore(
            total=85.5,
            freshness=90.0,
            latency=80.0,
            uptime=95.0,
            completeness=85.0,
            reliability=88.0
        )
        assert score.total == 85.5
        assert score.freshness == 90.0

    def test_data_lineage(self):
        """Test data lineage model"""
        lineage = DataLineage(
            providers=["yahoo_finance", "mock_provider"],
            arbitration_score=0.95,
            conflict_resolved=True,
            source_count=2
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
            progress=0.0
        )
        assert task.id == "task-123"
        assert task.status == TaskStatus.PENDING

    def test_arbitration_plan(self):
        """Test arbitration plan model"""
        plan = ArbitrationPlan(
            primary_provider="yahoo_finance",
            fallback_providers=["mock_provider"],
            estimated_latency_ms=100,
            timeout_ms=5000
        )
        assert plan.primary_provider == "yahoo_finance"
        assert len(plan.fallback_providers) == 1


class TestConfig:
    """Test configuration"""

    def test_settings_creation(self):
        """Test creating settings"""
        settings = Settings(
            fiml_env="development",
            redis_host="localhost",
            postgres_host="localhost"
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
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')
