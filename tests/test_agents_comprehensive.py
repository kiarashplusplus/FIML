"""
Comprehensive tests for agents module to achieve near 100% coverage

Tests focus on:
- orchestrator.py: AgentOrchestrator class and coordination
- health.py: WorkerMetrics, WorkerHealthMonitor, and circuit breakers
- workers.py: All specialized worker implementations

Production-focused tests ensuring reliability and error handling.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from fiml.agents.health import (
    WorkerHealthMonitor,
    WorkerMetrics,
    WorkerStatus,
    worker_health_monitor,
)
from fiml.agents.orchestrator import AgentOrchestrator, agent_orchestrator
from fiml.core.models import Asset, AssetType, DataType, Market


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_equity_asset():
    """Create a sample equity asset"""
    return Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US,
        exchange="NASDAQ",
        currency="USD"
    )


@pytest.fixture
def sample_crypto_asset():
    """Create a sample crypto asset"""
    return Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
        market=Market.CRYPTO,
        exchange="binance",
        currency="USDT"
    )


@pytest.fixture
def health_monitor():
    """Create a fresh WorkerHealthMonitor instance"""
    return WorkerHealthMonitor()


# ============================================================================
# WorkerMetrics Tests
# ============================================================================

class TestWorkerMetrics:
    """Test WorkerMetrics dataclass"""

    def test_worker_metrics_initialization(self):
        """Test basic WorkerMetrics initialization"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="fundamentals")

        assert metrics.worker_id == "test-1"
        assert metrics.worker_type == "fundamentals"
        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 0
        assert metrics.status == WorkerStatus.INITIALIZING
        assert metrics.created_at is not None

    def test_avg_execution_time_no_tasks(self):
        """Test average execution time with no completed tasks"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        assert metrics.avg_execution_time == 0.0

    def test_avg_execution_time_with_tasks(self):
        """Test average execution time calculation"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        metrics.record_task_success(2.0)
        metrics.record_task_success(4.0)
        metrics.record_task_success(6.0)

        assert metrics.avg_execution_time == 4.0
        assert metrics.tasks_completed == 3
        assert metrics.total_execution_time == 12.0

    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        # No tasks - should return 1.0
        assert metrics.success_rate == 1.0

        # With successes and failures
        metrics.record_task_success(1.0)
        metrics.record_task_success(1.0)
        metrics.record_task_failure("error")

        assert abs(metrics.success_rate - (2.0 / 3.0)) < 0.001
        assert abs(metrics.error_rate - (1.0 / 3.0)) < 0.001

    def test_record_task_success_updates_metrics(self):
        """Test that task success properly updates all metrics"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        initial_heartbeat = metrics.last_heartbeat

        metrics.record_task_success(5.0)

        assert metrics.tasks_completed == 1
        assert metrics.total_execution_time == 5.0
        assert metrics.min_execution_time == 5.0
        assert metrics.max_execution_time == 5.0
        assert metrics.last_task_at is not None
        assert metrics.last_heartbeat != initial_heartbeat

    def test_record_task_success_min_max_tracking(self):
        """Test min/max execution time tracking"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        metrics.record_task_success(10.0)
        metrics.record_task_success(2.0)
        metrics.record_task_success(15.0)

        assert metrics.min_execution_time == 2.0
        assert metrics.max_execution_time == 15.0

    def test_record_task_failure_limits_errors(self):
        """Test that error messages are limited to last 10"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        # Add 15 errors
        for i in range(15):
            metrics.record_task_failure(f"error_{i}")

        # Should keep only last 10
        assert len(metrics.error_messages) == 10
        assert "error_5" in metrics.error_messages[0]
        assert "error_14" in metrics.error_messages[-1]

    def test_record_task_timeout(self):
        """Test timeout recording"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        metrics.record_task_timeout()

        assert metrics.tasks_timeout == 1
        assert metrics.tasks_failed == 1

    def test_update_heartbeat(self):
        """Test heartbeat update"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        initial_heartbeat = metrics.last_heartbeat
        time.sleep(0.01)
        metrics.update_heartbeat()

        assert metrics.last_heartbeat != initial_heartbeat

    def test_update_status(self):
        """Test status update"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")

        metrics.update_status(WorkerStatus.HEALTHY)

        assert metrics.status == WorkerStatus.HEALTHY
        assert metrics.last_heartbeat is not None

    def test_is_healthy_no_heartbeat(self):
        """Test health check with no heartbeat"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")
        metrics.last_heartbeat = None

        assert metrics.is_healthy() is False

    def test_is_healthy_old_heartbeat(self):
        """Test health check with stale heartbeat"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")
        metrics.last_heartbeat = datetime.utcnow() - timedelta(seconds=200)

        assert metrics.is_healthy(max_heartbeat_age_seconds=120) is False

    def test_is_healthy_high_error_rate(self):
        """Test health check with high error rate"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")
        metrics.update_heartbeat()

        # Create high error rate (60%)
        metrics.record_task_success(1.0)
        metrics.record_task_failure("error 1")
        metrics.record_task_failure("error 2")
        metrics.record_task_failure("error 3")

        assert metrics.is_healthy() is False

    def test_is_healthy_unhealthy_status(self):
        """Test health check with unhealthy status"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")
        metrics.update_heartbeat()
        metrics.update_status(WorkerStatus.UNHEALTHY)

        assert metrics.is_healthy() is False

    def test_is_healthy_success(self):
        """Test health check passes when all criteria met"""
        metrics = WorkerMetrics(worker_id="test-1", worker_type="test")
        metrics.update_heartbeat()
        metrics.update_status(WorkerStatus.HEALTHY)

        # Good error rate
        metrics.record_task_success(1.0)
        metrics.record_task_success(1.0)
        metrics.record_task_failure("error")

        assert metrics.is_healthy() is True


# ============================================================================
# WorkerHealthMonitor Tests
# ============================================================================

class TestWorkerHealthMonitor:
    """Test WorkerHealthMonitor class"""

    def test_initialization(self, health_monitor):
        """Test monitor initialization"""
        assert health_monitor._metrics == {}
        assert health_monitor._failure_threshold > 0
        assert health_monitor._recovery_timeout > 0

    def test_register_worker(self, health_monitor):
        """Test worker registration"""
        metrics = health_monitor.register_worker("worker-1", "fundamentals")

        assert metrics.worker_id == "worker-1"
        assert metrics.worker_type == "fundamentals"
        assert "worker-1" in health_monitor._metrics

    def test_register_worker_duplicate(self, health_monitor, caplog):
        """Test registering same worker twice"""
        metrics1 = health_monitor.register_worker("worker-1", "fundamentals")
        metrics2 = health_monitor.register_worker("worker-1", "fundamentals")

        assert metrics1 is metrics2
        assert "already registered" in caplog.text

    def test_get_metrics(self, health_monitor):
        """Test retrieving worker metrics"""
        health_monitor.register_worker("worker-1", "fundamentals")

        metrics = health_monitor.get_metrics("worker-1")
        assert metrics is not None
        assert metrics.worker_id == "worker-1"

        # Non-existent worker
        assert health_monitor.get_metrics("nonexistent") is None

    def test_get_all_metrics(self, health_monitor):
        """Test retrieving all metrics"""
        health_monitor.register_worker("worker-1", "fundamentals")
        health_monitor.register_worker("worker-2", "technical")

        all_metrics = health_monitor.get_all_metrics()

        assert len(all_metrics) == 2
        assert "worker-1" in all_metrics
        assert "worker-2" in all_metrics

    def test_record_task_start(self, health_monitor):
        """Test recording task start"""
        health_monitor.register_worker("worker-1", "fundamentals")

        start_time = health_monitor.record_task_start("worker-1")

        assert isinstance(start_time, float)
        metrics = health_monitor.get_metrics("worker-1")
        assert metrics.tasks_in_progress == 1

    def test_record_task_complete_success(self, health_monitor):
        """Test recording successful task completion"""
        health_monitor.register_worker("worker-1", "fundamentals")

        start_time = health_monitor.record_task_start("worker-1")
        time.sleep(0.01)
        health_monitor.record_task_complete("worker-1", start_time, success=True)

        metrics = health_monitor.get_metrics("worker-1")
        assert metrics.tasks_completed == 1
        assert metrics.tasks_in_progress == 0
        assert metrics.total_execution_time > 0

    def test_record_task_complete_failure(self, health_monitor):
        """Test recording failed task completion"""
        health_monitor.register_worker("worker-1", "fundamentals")

        start_time = health_monitor.record_task_start("worker-1")
        health_monitor.record_task_complete("worker-1", start_time, success=False, error="Test error")

        metrics = health_monitor.get_metrics("worker-1")
        assert metrics.tasks_failed == 1
        assert metrics.tasks_in_progress == 0
        assert len(metrics.error_messages) == 1

    def test_record_task_complete_unknown_worker(self, health_monitor, caplog):
        """Test recording task for unknown worker"""
        health_monitor.record_task_complete("unknown", time.time(), success=True)

        assert "Unknown worker" in caplog.text

    def test_record_task_timeout(self, health_monitor):
        """Test recording task timeout"""
        health_monitor.register_worker("worker-1", "fundamentals")

        start_time = health_monitor.record_task_start("worker-1")
        health_monitor.record_task_timeout("worker-1", start_time)

        metrics = health_monitor.get_metrics("worker-1")
        assert metrics.tasks_timeout == 1
        assert metrics.tasks_failed == 1

    def test_circuit_breaker_opens_on_failures(self, health_monitor):
        """Test circuit breaker opens after threshold failures"""
        health_monitor.register_worker("worker-1", "fundamentals")
        health_monitor._failure_threshold = 3

        # Record failures to exceed threshold
        for i in range(3):
            start_time = time.time()
            health_monitor.record_task_complete("worker-1", start_time, success=False, error=f"Error {i}")

        assert health_monitor.is_circuit_open("worker-1") is True
        
        # Check worker status
        metrics = health_monitor.get_metrics("worker-1")
        assert metrics.status == WorkerStatus.UNHEALTHY

    def test_circuit_breaker_half_open_after_timeout(self, health_monitor):
        """Test circuit breaker transitions to half-open"""
        health_monitor.register_worker("worker-1", "fundamentals")
        health_monitor._failure_threshold = 2
        health_monitor._recovery_timeout = 0.1  # 100ms for testing

        # Open circuit
        for i in range(2):
            health_monitor.record_task_complete("worker-1", time.time(), success=False)

        assert health_monitor.is_circuit_open("worker-1") is True

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should be half-open now
        assert health_monitor.is_circuit_open("worker-1") is False
        assert health_monitor._circuit_breakers["worker-1"]["state"] == "half-open"

    def test_circuit_breaker_closes_on_success(self, health_monitor):
        """Test circuit breaker closes after success in half-open state"""
        health_monitor.register_worker("worker-1", "fundamentals")
        health_monitor._failure_threshold = 2
        health_monitor._recovery_timeout = 0.1

        # Open circuit
        for i in range(2):
            health_monitor.record_task_complete("worker-1", time.time(), success=False)

        # Wait for half-open
        time.sleep(0.15)
        health_monitor.is_circuit_open("worker-1")  # Transitions to half-open

        # Record success
        health_monitor.record_task_complete("worker-1", time.time(), success=True)

        # Should be closed
        assert health_monitor._circuit_breakers["worker-1"]["state"] == "closed"
        assert health_monitor._circuit_breakers["worker-1"]["failures"] == 0

        metrics = health_monitor.get_metrics("worker-1")
        assert metrics.status == WorkerStatus.HEALTHY

    def test_circuit_breaker_gradual_failure_reduction(self, health_monitor):
        """Test gradual failure count reduction on success"""
        health_monitor.register_worker("worker-1", "fundamentals")

        # Record failure
        health_monitor.record_task_complete("worker-1", time.time(), success=False)
        assert health_monitor._circuit_breakers["worker-1"]["failures"] == 1

        # Record success - should reduce failure count
        health_monitor.record_task_complete("worker-1", time.time(), success=True)
        assert health_monitor._circuit_breakers["worker-1"]["failures"] == 0

    def test_get_health_summary_empty(self, health_monitor):
        """Test health summary with no workers"""
        summary = health_monitor.get_health_summary()

        assert summary["total_workers"] == 0
        assert summary["healthy_workers"] == 0
        assert summary["overall_success_rate"] == 1.0

    def test_get_health_summary_with_workers(self, health_monitor):
        """Test comprehensive health summary"""
        # Register workers of different types
        health_monitor.register_worker("fund-1", "fundamentals")
        health_monitor.register_worker("fund-2", "fundamentals")
        health_monitor.register_worker("tech-1", "technical")

        # Record some tasks
        for worker_id in ["fund-1", "fund-2", "tech-1"]:
            metrics = health_monitor.get_metrics(worker_id)
            metrics.update_heartbeat()
            metrics.update_status(WorkerStatus.HEALTHY)
            metrics.record_task_success(1.0)
            metrics.record_task_success(1.5)

        summary = health_monitor.get_health_summary()

        assert summary["total_workers"] == 3
        assert summary["healthy_workers"] == 3
        assert summary["total_tasks"] == 6
        assert summary["total_successes"] == 6
        assert summary["overall_success_rate"] == 1.0

        # Check by-type stats
        assert "fundamentals" in summary["by_type"]
        assert summary["by_type"]["fundamentals"]["total"] == 2
        assert summary["by_type"]["fundamentals"]["healthy"] == 2

    def test_get_unhealthy_workers(self, health_monitor):
        """Test getting list of unhealthy workers"""
        health_monitor.register_worker("worker-1", "fundamentals")
        health_monitor.register_worker("worker-2", "technical")

        # Make worker-1 unhealthy
        metrics1 = health_monitor.get_metrics("worker-1")
        metrics1.last_heartbeat = datetime.utcnow() - timedelta(seconds=200)

        # Keep worker-2 healthy
        metrics2 = health_monitor.get_metrics("worker-2")
        metrics2.update_heartbeat()
        metrics2.update_status(WorkerStatus.HEALTHY)

        unhealthy = health_monitor.get_unhealthy_workers()

        assert "worker-1" in unhealthy
        assert "worker-2" not in unhealthy


# ============================================================================
# AgentOrchestrator Tests
# ============================================================================

class TestAgentOrchestrator:
    """Test AgentOrchestrator class"""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly"""
        orchestrator = AgentOrchestrator()

        assert orchestrator.initialized is False
        assert orchestrator.workers == {}

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, caplog):
        """Test initializing when already initialized"""
        orchestrator = AgentOrchestrator()
        orchestrator.initialized = True

        await orchestrator.initialize()

        assert "already initialized" in caplog.text

    @pytest.mark.asyncio
    async def test_initialize_timeout(self):
        """Test initialization timeout handling"""
        orchestrator = AgentOrchestrator()

        with patch("fiml.agents.orchestrator.ray.is_initialized", return_value=False):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                await orchestrator.initialize()

                assert orchestrator.initialized is False

    @pytest.mark.asyncio
    async def test_initialize_exception(self, caplog):
        """Test initialization exception handling"""
        orchestrator = AgentOrchestrator()

        with patch("fiml.agents.orchestrator.ray.is_initialized", side_effect=Exception("Test error")):
            await orchestrator.initialize()

            assert orchestrator.initialized is False
            assert "Failed to initialize" in caplog.text

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test orchestrator shutdown"""
        orchestrator = AgentOrchestrator()
        orchestrator.initialized = True

        with patch("fiml.agents.orchestrator.ray.is_initialized", return_value=True):
            with patch("fiml.agents.orchestrator.ray.shutdown") as mock_shutdown:
                await orchestrator.shutdown()

                mock_shutdown.assert_called_once()
                assert orchestrator.initialized is False

    @pytest.mark.asyncio
    async def test_analyze_asset_not_initialized(self, sample_equity_asset):
        """Test analyzing asset when not initialized"""
        orchestrator = AgentOrchestrator()

        with pytest.raises(RuntimeError, match="not initialized"):
            await orchestrator.analyze_asset(sample_equity_asset)

    @pytest.mark.asyncio
    async def test_analyze_asset_with_mock_workers(self, sample_equity_asset):
        """Test asset analysis with mocked workers"""
        orchestrator = AgentOrchestrator()
        orchestrator.initialized = True

        # Mock worker
        mock_worker = MagicMock()
        mock_worker.process = MagicMock()
        mock_worker.process.remote = AsyncMock(return_value={"score": 7.5, "recommendation": "buy"})

        orchestrator.workers = {"fundamentals": [mock_worker]}

        result = await orchestrator.analyze_asset(sample_equity_asset, agents=["fundamentals"])

        assert "asset" in result
        assert result["asset"] == "AAPL"
        assert "analyses" in result
        assert "aggregate" in result
        assert "fundamentals" in result["analyses"]

    @pytest.mark.asyncio
    async def test_analyze_asset_worker_failure(self, sample_equity_asset):
        """Test handling worker failures during analysis"""
        orchestrator = AgentOrchestrator()
        orchestrator.initialized = True

        # Mock failing worker
        mock_worker = MagicMock()
        mock_worker.process = MagicMock()
        mock_worker.process.remote = AsyncMock(side_effect=Exception("Worker failed"))

        orchestrator.workers = {"fundamentals": [mock_worker]}

        result = await orchestrator.analyze_asset(sample_equity_asset)

        assert "analyses" in result
        assert "fundamentals" in result["analyses"]
        assert "error" in result["analyses"]["fundamentals"]

    @pytest.mark.asyncio
    async def test_analyze_multiple_assets(self, sample_equity_asset, sample_crypto_asset):
        """Test analyzing multiple assets in parallel"""
        orchestrator = AgentOrchestrator()
        orchestrator.initialized = True

        # Mock worker
        mock_worker = MagicMock()
        mock_worker.process = MagicMock()
        mock_worker.process.remote = AsyncMock(return_value={"score": 7.0})

        orchestrator.workers = {"technical": [mock_worker]}

        results = await orchestrator.analyze_multiple(
            [sample_equity_asset, sample_crypto_asset],
            agents=["technical"]
        )

        assert len(results) == 2
        assert all("asset" in r for r in results)

    def test_aggregate_results_no_scores(self):
        """Test aggregation with no valid scores"""
        orchestrator = AgentOrchestrator()

        results = {
            "fundamentals": {"error": "failed"},
            "technical": {"data": "no_score"}
        }

        aggregate = orchestrator._aggregate_results(results)

        assert aggregate["overall_score"] == 0
        assert aggregate["agent_count"] == 2
        assert aggregate["scores"] == []

    def test_aggregate_results_with_scores(self):
        """Test proper score aggregation"""
        orchestrator = AgentOrchestrator()

        results = {
            "fundamentals": {"score": 8.0},
            "technical": {"score": 7.0},
            "sentiment": {"score": 6.5}
        }

        aggregate = orchestrator._aggregate_results(results)

        assert aggregate["overall_score"] == 7.17
        assert len(aggregate["scores"]) == 3
        assert aggregate["agent_count"] == 3

    def test_aggregate_results_recommendations(self):
        """Test recommendation generation based on scores"""
        orchestrator = AgentOrchestrator()

        test_cases = [
            ({"a": {"score": 9.0}}, "strong_buy"),
            ({"a": {"score": 7.0}}, "buy"),
            ({"a": {"score": 6.0}}, "hold"),
            ({"a": {"score": 5.0}}, "sell"),
            ({"a": {"score": 3.0}}, "strong_sell"),
        ]

        for results, expected_recommendation in test_cases:
            aggregate = orchestrator._aggregate_results(results)
            assert aggregate["recommendation"] == expected_recommendation

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self):
        """Test health check when not initialized"""
        orchestrator = AgentOrchestrator()

        health = await orchestrator.health_check()

        assert health["status"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_health_check_with_workers(self):
        """Test health check with workers"""
        orchestrator = AgentOrchestrator()
        orchestrator.initialized = True

        # Mock worker
        mock_worker = MagicMock()
        mock_worker.health_check = MagicMock()
        mock_worker.health_check.remote = AsyncMock(return_value={"status": "healthy"})

        orchestrator.workers = {"fundamentals": [mock_worker]}

        health = await orchestrator.health_check()

        assert health["status"] == "healthy"
        assert "workers" in health
        assert "fundamentals" in health["workers"]

    @pytest.mark.asyncio
    async def test_health_check_worker_error(self):
        """Test health check handles worker errors"""
        orchestrator = AgentOrchestrator()
        orchestrator.initialized = True

        # Mock failing worker
        mock_worker = MagicMock()
        mock_worker.health_check = MagicMock()
        mock_worker.health_check.remote = AsyncMock(side_effect=Exception("Health check failed"))

        orchestrator.workers = {"fundamentals": [mock_worker]}

        health = await orchestrator.health_check()

        assert "workers" in health
        assert "error" in health["workers"]["fundamentals"][0]


# ============================================================================
# Worker Status Enum Tests
# ============================================================================

class TestWorkerStatus:
    """Test WorkerStatus enum"""

    def test_worker_status_values(self):
        """Test all WorkerStatus enum values"""
        assert WorkerStatus.HEALTHY == "healthy"
        assert WorkerStatus.DEGRADED == "degraded"
        assert WorkerStatus.UNHEALTHY == "unhealthy"
        assert WorkerStatus.INITIALIZING == "initializing"
        assert WorkerStatus.SHUTDOWN == "shutdown"

    def test_worker_status_membership(self):
        """Test WorkerStatus enum membership"""
        assert "healthy" in WorkerStatus.__members__.values()
        assert WorkerStatus.HEALTHY in WorkerStatus


# ============================================================================
# Global Instances Tests
# ============================================================================

class TestGlobalInstances:
    """Test global singleton instances"""

    def test_worker_health_monitor_singleton(self):
        """Test worker_health_monitor global instance"""
        assert worker_health_monitor is not None
        assert isinstance(worker_health_monitor, WorkerHealthMonitor)

    def test_agent_orchestrator_singleton(self):
        """Test agent_orchestrator global instance"""
        assert agent_orchestrator is not None
        assert isinstance(agent_orchestrator, AgentOrchestrator)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for agents module"""

    def test_health_monitor_with_multiple_worker_types(self, health_monitor):
        """Test health monitor managing different worker types"""
        # Register various worker types
        worker_types = ["fundamentals", "technical", "sentiment", "macro", "risk"]

        for i, worker_type in enumerate(worker_types):
            health_monitor.register_worker(f"{worker_type}-1", worker_type)
            health_monitor.register_worker(f"{worker_type}-2", worker_type)

        # Record tasks for each
        for worker_id in health_monitor.get_all_metrics().keys():
            metrics = health_monitor.get_metrics(worker_id)
            metrics.update_heartbeat()
            metrics.record_task_success(1.0)

        summary = health_monitor.get_health_summary()

        assert summary["total_workers"] == 10
        assert len(summary["by_type"]) == 5
        for worker_type in worker_types:
            assert summary["by_type"][worker_type]["total"] == 2

    def test_circuit_breaker_recovery_flow(self, health_monitor):
        """Test complete circuit breaker recovery flow"""
        health_monitor.register_worker("worker-1", "test")
        health_monitor._failure_threshold = 3
        health_monitor._recovery_timeout = 0.1

        # Fail enough times to open circuit
        for i in range(3):
            health_monitor.record_task_complete("worker-1", time.time(), success=False)

        assert health_monitor.is_circuit_open("worker-1") is True

        # Wait for recovery window
        time.sleep(0.15)

        # Should be half-open
        assert health_monitor.is_circuit_open("worker-1") is False
        assert health_monitor._circuit_breakers["worker-1"]["state"] == "half-open"

        # Success should close circuit
        health_monitor.record_task_complete("worker-1", time.time(), success=True)
        assert health_monitor._circuit_breakers["worker-1"]["state"] == "closed"

        # Verify worker is healthy again
        metrics = health_monitor.get_metrics("worker-1")
        assert metrics.status == WorkerStatus.HEALTHY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
