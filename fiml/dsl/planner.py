"""
Execution Planner - Converts parsed DSL into DAG execution plan
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fiml.core.logging import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """Task types in execution plan"""

    FETCH_PRICE = "fetch_price"
    FETCH_OHLCV = "fetch_ohlcv"
    FETCH_FUNDAMENTALS = "fetch_fundamentals"
    FETCH_NEWS = "fetch_news"
    COMPUTE_TECHNICAL = "compute_technical"
    COMPUTE_SENTIMENT = "compute_sentiment"
    FILTER_ASSETS = "filter_assets"
    COMPARE_METRICS = "compare_metrics"
    AGGREGATE = "aggregate"


@dataclass
class ExecutionTask:
    """A single task in the execution plan"""

    id: str = field(default_factory=lambda: str(uuid4()))
    type: TaskType = TaskType.FETCH_PRICE
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    estimated_duration_ms: int = 100


@dataclass
class ExecutionPlan:
    """DAG execution plan"""

    query: str
    tasks: List[ExecutionTask] = field(default_factory=list)
    root_task_ids: List[str] = field(default_factory=list)

    def add_task(self, task: ExecutionTask) -> str:
        """Add task to plan"""
        self.tasks.append(task)
        if not task.dependencies:
            self.root_task_ids.append(task.id)
        return task.id

    def get_task(self, task_id: str) -> Optional[ExecutionTask]:
        """Get task by ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_executable_tasks(self, completed: Set[str]) -> List[ExecutionTask]:
        """Get tasks that can be executed now"""
        executable = []
        for task in self.tasks:
            if task.id in completed:
                continue
            # Check if all dependencies completed
            if all(dep in completed for dep in task.dependencies):
                executable.append(task)
        return executable

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        return {
            "query": self.query,
            "tasks": [
                {
                    "id": t.id,
                    "type": t.type.value,
                    "params": t.params,
                    "dependencies": t.dependencies,
                    "priority": t.priority,
                    "estimated_duration_ms": t.estimated_duration_ms,
                }
                for t in self.tasks
            ],
            "root_task_ids": self.root_task_ids,
        }


class ExecutionPlanner:
    """
    Converts parsed DSL into executable DAG plan

    Responsibilities:
    - Build task dependency graph
    - Optimize execution order
    - Estimate resource requirements
    """

    def __init__(self):
        pass

    def plan(self, parsed_query: Dict[str, Any], query_str: str) -> ExecutionPlan:
        """
        Create execution plan from parsed query

        Args:
            parsed_query: Output from FKDSLParser
            query_str: Original query string

        Returns:
            ExecutionPlan with tasks and dependencies
        """
        plan = ExecutionPlan(query=query_str)

        query_type = parsed_query.get("type")

        if query_type == "FIND":
            self._plan_find(plan, parsed_query)
        elif query_type == "ANALYZE":
            self._plan_analyze(plan, parsed_query)
        elif query_type == "COMPARE":
            self._plan_compare(plan, parsed_query)
        elif query_type == "GET":
            self._plan_get(plan, parsed_query)
        else:
            logger.warning(f"Unknown query type: {query_type}")

        logger.info("Execution plan created", tasks=len(plan.tasks), query=query_str[:50])
        return plan

    def _plan_find(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """Plan FIND query execution"""
        args = parsed.get("args", [])
        if len(args) < 2:
            return

        asset_spec = args[0]
        conditions = args[1]

        # Task 1: Fetch asset data
        fetch_task = ExecutionTask(
            type=TaskType.FETCH_PRICE,
            params={"asset": asset_spec},
            priority=1,
            estimated_duration_ms=500,
        )
        fetch_id = plan.add_task(fetch_task)

        # Task 2: Apply filters
        filter_task = ExecutionTask(
            type=TaskType.FILTER_ASSETS,
            params={"conditions": conditions},
            dependencies=[fetch_id],
            priority=2,
            estimated_duration_ms=100,
        )
        plan.add_task(filter_task)

    def _plan_analyze(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """Plan ANALYZE query execution"""
        args = parsed.get("args", [])
        if len(args) < 2:
            return

        asset_spec = args[0]
        analysis_type = args[1]

        # Task 1: Fetch price data
        price_task = ExecutionTask(
            type=TaskType.FETCH_PRICE,
            params={"asset": asset_spec},
            priority=1,
            estimated_duration_ms=500,
        )
        price_id = plan.add_task(price_task)

        # Task 2: Fetch OHLCV for technical analysis
        ohlcv_task = ExecutionTask(
            type=TaskType.FETCH_OHLCV,
            params={"asset": asset_spec, "timeframe": "1d", "limit": 100},
            priority=1,
            estimated_duration_ms=800,
        )
        ohlcv_id = plan.add_task(ohlcv_task)

        # Task 3: Compute analysis
        if analysis_type == "technicals":
            compute_task = ExecutionTask(
                type=TaskType.COMPUTE_TECHNICAL,
                params={"indicators": ["RSI", "MACD", "SMA", "EMA"]},
                dependencies=[ohlcv_id],
                priority=2,
                estimated_duration_ms=300,
            )
            plan.add_task(compute_task)

        elif analysis_type == "fundamentals":
            fund_task = ExecutionTask(
                type=TaskType.FETCH_FUNDAMENTALS,
                params={"asset": asset_spec},
                dependencies=[price_id],
                priority=2,
                estimated_duration_ms=1000,
            )
            plan.add_task(fund_task)

    def _plan_compare(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """Plan COMPARE query execution"""
        args = parsed.get("args", [])
        if len(args) < 2:
            return

        assets = args[0]
        metrics = args[1]

        # Fetch data for each asset in parallel
        fetch_ids = []
        for asset in assets:
            task = ExecutionTask(
                type=TaskType.FETCH_FUNDAMENTALS,
                params={"asset": asset},
                priority=1,
                estimated_duration_ms=800,
            )
            fetch_ids.append(plan.add_task(task))

        # Compare metrics
        compare_task = ExecutionTask(
            type=TaskType.COMPARE_METRICS,
            params={"metrics": metrics},
            dependencies=fetch_ids,
            priority=2,
            estimated_duration_ms=200,
        )
        plan.add_task(compare_task)

    def _plan_get(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """Plan GET query execution"""
        args = parsed.get("args", [])
        if not args:
            return

        data_type = args[0]

        # Simple fetch task
        if data_type == "PRICE":
            task_type = TaskType.FETCH_PRICE
        elif data_type == "OHLCV":
            task_type = TaskType.FETCH_OHLCV
        elif data_type == "FUNDAMENTALS":
            task_type = TaskType.FETCH_FUNDAMENTALS
        elif data_type == "NEWS":
            task_type = TaskType.FETCH_NEWS
        else:
            task_type = TaskType.FETCH_PRICE

        task = ExecutionTask(
            type=task_type, params={"data": args}, priority=1, estimated_duration_ms=500
        )
        plan.add_task(task)


# Global planner instance
execution_planner = ExecutionPlanner()
