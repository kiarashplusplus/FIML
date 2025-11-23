"""
FK-DSL Executor - Executes planned tasks
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from fiml.core.exceptions import FKDSLExecutionError
from fiml.core.logging import get_logger
from fiml.core.models import TaskInfo, TaskStatus
from fiml.dsl.planner import ExecutionPlan, ExecutionTask, TaskType

logger = get_logger(__name__)


class ExecutionTaskInfo(BaseModel):
    """Internal task execution tracking"""

    task_id: str
    status: TaskStatus
    query: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_steps: int = 0
    completed_steps: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskExecutor:
    """Executes individual tasks"""

    def __init__(self) -> None:
        self.providers = None  # Would inject provider registry

    async def execute(self, task: ExecutionTask, context: Dict[str, Any]) -> Any:
        """
        Execute a single task

        Args:
            task: Task to execute
            context: Shared execution context with results from dependencies

        Returns:
            Task result
        """
        logger.debug("Executing task", task_id=task.id, type=task.type.value)

        try:
            if task.type == TaskType.FETCH_PRICE:
                return await self._fetch_price(task, context)
            elif task.type == TaskType.FETCH_OHLCV:
                return await self._fetch_ohlcv(task, context)
            elif task.type == TaskType.FETCH_FUNDAMENTALS:
                return await self._fetch_fundamentals(task, context)
            elif task.type == TaskType.FETCH_NEWS:
                return await self._fetch_news(task, context)
            elif task.type == TaskType.COMPUTE_TECHNICAL:
                return await self._compute_technical(task, context)
            elif task.type == TaskType.FILTER_ASSETS:
                return await self._filter_assets(task, context)
            elif task.type == TaskType.COMPARE_METRICS:
                return await self._compare_metrics(task, context)
            else:
                logger.warning(f"Unknown task type: {task.type}")
                return None

        except Exception as e:
            logger.error(f"Task execution failed: {e}", task_id=task.id)
            raise FKDSLExecutionError(f"Task {task.id} failed: {e}")

    async def _fetch_price(self, task: ExecutionTask, context: Dict) -> Dict[str, Any]:
        """Fetch price data"""
        # Mock implementation - would use provider registry
        await asyncio.sleep(0.1)
        return {
            "symbol": "AAPL",
            "price": 150.25,
            "change": 2.5,
            "change_percent": 1.69,
        }

    async def _fetch_ohlcv(self, task: ExecutionTask, context: Dict) -> List[Dict]:
        """Fetch OHLCV data"""
        await asyncio.sleep(0.2)
        return [
            {"time": "2024-01-01", "open": 145, "high": 152, "low": 144, "close": 150, "volume": 1000000}
        ]

    async def _fetch_fundamentals(self, task: ExecutionTask, context: Dict) -> Dict:
        """Fetch fundamentals"""
        await asyncio.sleep(0.3)
        return {"pe_ratio": 25.5, "eps": 6.12, "market_cap": 2500000000000}

    async def _fetch_news(self, task: ExecutionTask, context: Dict) -> List[Dict]:
        """Fetch news"""
        await asyncio.sleep(0.15)
        return [{"title": "Company announces earnings", "sentiment": 0.8}]

    async def _compute_technical(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compute technical indicators"""
        await asyncio.sleep(0.1)
        return {"rsi": 45.2, "macd": {"macd": 1.2, "signal": 0.8, "histogram": 0.4}}

    async def _filter_assets(self, task: ExecutionTask, context: Dict) -> List[Dict]:
        """Filter assets by conditions"""
        await asyncio.sleep(0.05)
        return [{"symbol": "AAPL", "matches": True}]

    async def _compare_metrics(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compare metrics across assets"""
        await asyncio.sleep(0.05)
        return {"comparison": [{"asset": "AAPL", "pe": 25.5}, {"asset": "MSFT", "pe": 30.2}]}


class FKDSLExecutor:
    """
    Executes FK-DSL queries using DAG-based execution

    Features:
    - Parallel task execution
    - Dependency management
    - Progress tracking
    - Result caching
    """

    def __init__(self) -> None:
        self.task_executor = TaskExecutor()
        self.active_executions: Dict[str, ExecutionTaskInfo] = {}

    async def execute_async(self, plan: ExecutionPlan) -> str:
        """
        Start async execution of plan

        Args:
            plan: Execution plan

        Returns:
            Task ID for tracking
        """
        task_id = str(uuid4())

        task_info = ExecutionTaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            query=plan.query,
            total_steps=len(plan.tasks),
            completed_steps=0,
        )

        self.active_executions[task_id] = task_info

        # Execute in background
        asyncio.create_task(self._execute_plan(task_id, plan))

        logger.info("Async execution started", task_id=task_id, query=plan.query[:50])
        return task_id

    async def _execute_plan(self, task_id: str, plan: ExecutionPlan) -> None:
        """Execute plan DAG"""
        task_info = self.active_executions[task_id]
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.now(timezone.utc)

        completed: Set[str] = set()
        results: Dict[str, Any] = {}
        context: Dict[str, Any] = {}

        try:
            # Execute tasks in dependency order
            while len(completed) < len(plan.tasks):
                # Get executable tasks
                executable = plan.get_executable_tasks(completed)

                if not executable:
                    if len(completed) < len(plan.tasks):
                        raise FKDSLExecutionError("Circular dependency detected")
                    break

                # Execute in parallel
                tasks = [
                    self.task_executor.execute(task, context)
                    for task in executable
                ]

                task_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Store results
                for task, result in zip(executable, task_results, strict=False):
                    if isinstance(result, Exception):
                        raise result
                    results[task.id] = result
                    completed.add(task.id)
                    context[task.id] = result

                # Update progress
                task_info.completed_steps = len(completed)

            # Success
            task_info.status = TaskStatus.COMPLETED
            task_info.result = results
            task_info.completed_at = datetime.now(timezone.utc)

            logger.info("Execution completed", task_id=task_id)

        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error = str(e)
            task_info.completed_at = datetime.now(timezone.utc)
            logger.error(f"Execution failed: {e}", task_id=task_id)

    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get execution status"""
        internal_info = self.active_executions.get(task_id)
        if internal_info is None:
            return None

        # Convert internal info to TaskInfo
        return TaskInfo(
            id=internal_info.task_id,
            type="dsl_execution",
            status=internal_info.status,
            resource_url=f"/api/tasks/{task_id}",
            progress=internal_info.completed_steps / max(internal_info.total_steps, 1) if internal_info.total_steps > 0 else 0.0,
            created_at=internal_info.created_at,
            updated_at=internal_info.completed_at or internal_info.started_at or internal_info.created_at,
            query=internal_info.query,
            completed_steps=internal_info.completed_steps,
            total_steps=internal_info.total_steps,
            started_at=internal_info.started_at,
            completed_at=internal_info.completed_at,
            result=internal_info.result,
            error=internal_info.error,
        )

    async def execute_sync(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Execute plan synchronously and return results"""
        task_id = await self.execute_async(plan)

        # Wait for completion
        while True:
            internal_info = self.active_executions.get(task_id)
            if internal_info and internal_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
            await asyncio.sleep(0.1)

        internal_info = self.active_executions.get(task_id)
        if internal_info is None:
            raise FKDSLExecutionError(f"Task {task_id} not found")

        if internal_info.status == TaskStatus.FAILED:
            raise FKDSLExecutionError(internal_info.error)

        return internal_info.result if internal_info.result else {}


# Global executor instance
fk_dsl_executor = FKDSLExecutor()
