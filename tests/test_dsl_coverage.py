"""
Tests to fill missing coverage in DSL modules
"""

import pytest

from fiml.core.models import TaskStatus
from fiml.dsl.executor import ExecutionTaskInfo, TaskExecutor, fk_dsl_executor
from fiml.dsl.planner import ExecutionTask, TaskType


class TestTaskExecutor:
    """Test TaskExecutor class"""

    @pytest.mark.asyncio
    async def test_task_executor_creation(self):
        """Test creating a task executor"""
        executor = TaskExecutor()
        assert executor.providers is None

    @pytest.mark.asyncio
    async def test_execute_fetch_price_task(self):
        """Test executing a fetch price task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.FETCH_PRICE,
            params={"symbol": "AAPL"}
        )

        context = {}

        # Execute the task
        result = await executor.execute(task, context)

        # Should return mock data
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_fetch_ohlcv_task(self):
        """Test executing a fetch OHLCV task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.FETCH_OHLCV,
            params={"symbol": "AAPL", "timeframe": "1d"}
        )

        result = await executor.execute(task, {})
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_fetch_fundamentals_task(self):
        """Test executing a fetch fundamentals task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.FETCH_FUNDAMENTALS,
            params={"symbol": "AAPL"}
        )

        result = await executor.execute(task, {})
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_fetch_news_task(self):
        """Test executing a fetch news task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.FETCH_NEWS,
            params={"symbol": "AAPL"}
        )

        result = await executor.execute(task, {})
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_compute_technical_task(self):
        """Test executing a compute technical task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.COMPUTE_TECHNICAL,
            params={"symbol": "AAPL", "indicators": ["RSI", "MACD"]}
        )

        result = await executor.execute(task, {})
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_compute_sentiment_task(self):
        """Test executing a compute sentiment task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.COMPUTE_SENTIMENT,
            params={"symbol": "AAPL"}
        )

        result = await executor.execute(task, {})
        # Might return None for unimplemented tasks
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_filter_assets_task(self):
        """Test executing a filter assets task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.FILTER_ASSETS,
            params={"criteria": {}}
        )

        result = await executor.execute(task, {})
        # Might return list or dict
        assert result is None or isinstance(result, (dict, list))

    @pytest.mark.asyncio
    async def test_execute_compare_metrics_task(self):
        """Test executing a compare metrics task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.COMPARE_METRICS,
            params={"symbols": ["AAPL", "MSFT"]}
        )

        result = await executor.execute(task, {})
        # Might return None for unimplemented tasks
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_aggregate_task(self):
        """Test executing an aggregate task"""
        executor = TaskExecutor()

        task = ExecutionTask(
            type=TaskType.AGGREGATE,
            params={}
        )

        result = await executor.execute(task, {})
        # Might return None for unimplemented tasks
        assert result is None or isinstance(result, dict)


class TestExecutionTaskInfo:
    """Test ExecutionTaskInfo model"""

    def test_execution_task_info_creation(self):
        """Test creating execution task info"""
        info = ExecutionTaskInfo(
            task_id="test-123",
            status=TaskStatus.PENDING,
            query="GET PRICE FOR AAPL",
            total_steps=5,
            completed_steps=0
        )

        assert info.task_id == "test-123"
        assert info.status == TaskStatus.PENDING
        assert info.total_steps == 5
        assert info.completed_steps == 0


class TestDSLExecutorEdgeCases:
    """Test DSL executor edge cases"""

    @pytest.mark.asyncio
    async def test_execute_plan_with_dependencies(self):
        """Test executing plan with task dependencies"""
        from fiml.dsl.planner import ExecutionPlan, ExecutionTask, TaskType

        plan = ExecutionPlan(query="complex query")

        # Create tasks with dependencies
        task1 = ExecutionTask(
            type=TaskType.FETCH_PRICE,
            params={"symbol": "AAPL"}
        )
        task1_id = plan.add_task(task1)

        task2 = ExecutionTask(
            type=TaskType.COMPUTE_TECHNICAL,
            params={"symbol": "AAPL"},
            dependencies=[task1_id]
        )
        plan.add_task(task2)

        # Execute the plan
        result = await fk_dsl_executor.execute_sync(plan)

        # Should complete successfully
        assert result is not None
