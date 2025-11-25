"""
Execution Planner - Converts parsed DSL into DAG execution plan

Supports Blueprint-specified query types:
- EVALUATE: Single asset analysis with multiple metrics
- COMPARE: Cross-asset comparison (both new and legacy syntax)
- MACRO: Macroeconomic regression/correlation analysis
- CORRELATE: Correlation analysis between assets
- SCAN: Market screening with conditions

Also supports legacy query types:
- FIND, ANALYZE, TRACK, GET
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fiml.core.logging import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """Task types in execution plan"""

    # Data fetching tasks
    FETCH_PRICE = "fetch_price"
    FETCH_OHLCV = "fetch_ohlcv"
    FETCH_FUNDAMENTALS = "fetch_fundamentals"
    FETCH_NEWS = "fetch_news"
    FETCH_MACRO = "fetch_macro"

    # Computation tasks
    COMPUTE_TECHNICAL = "compute_technical"
    COMPUTE_SENTIMENT = "compute_sentiment"
    COMPUTE_VOLATILITY = "compute_volatility"
    COMPUTE_CORRELATION = "compute_correlation"
    COMPUTE_REGRESSION = "compute_regression"

    # Analysis tasks
    FILTER_ASSETS = "filter_assets"
    COMPARE_METRICS = "compare_metrics"
    SCAN_MARKET = "scan_market"
    AGGREGATE = "aggregate"

    # Narrative generation
    GENERATE_NARRATIVE = "generate_narrative"


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
    query_type: str = ""
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

    def get_estimated_duration_ms(self) -> int:
        """Get estimated total duration based on parallel execution"""
        if not self.tasks:
            return 0

        # Calculate critical path (longest path through DAG)
        task_map = {t.id: t for t in self.tasks}
        memo: Dict[str, int] = {}

        def get_duration(task_id: str) -> int:
            if task_id in memo:
                return memo[task_id]

            task = task_map.get(task_id)
            if not task:
                return 0

            dep_durations = [get_duration(dep) for dep in task.dependencies]
            max_dep = max(dep_durations) if dep_durations else 0
            duration = max_dep + task.estimated_duration_ms
            memo[task_id] = duration
            return duration

        # Find maximum duration across all terminal tasks
        return max(get_duration(t.id) for t in self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        return {
            "query": self.query,
            "query_type": self.query_type,
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
            "estimated_total_duration_ms": self.get_estimated_duration_ms(),
        }


class ExecutionPlanner:
    """
    Converts parsed DSL into executable DAG plan

    Responsibilities:
    - Build task dependency graph
    - Optimize execution order
    - Estimate resource requirements

    Supports:
    - EVALUATE: Comprehensive asset analysis
    - COMPARE: Cross-asset comparison
    - MACRO: Macroeconomic analysis
    - CORRELATE: Correlation analysis
    - SCAN: Market screening
    - FIND, ANALYZE, TRACK, GET: Legacy queries
    """

    def __init__(self) -> None:
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
        query_type = parsed_query.get("type", "")
        plan = ExecutionPlan(query=query_str, query_type=query_type)

        # Route to appropriate planner based on query type
        planner_map = {
            "EVALUATE": self._plan_evaluate,
            "COMPARE": self._plan_compare,
            "MACRO": self._plan_macro,
            "CORRELATE": self._plan_correlate,
            "SCAN": self._plan_scan,
            "FIND": self._plan_find,
            "ANALYZE": self._plan_analyze,
            "TRACK": self._plan_track,
            "GET": self._plan_get,
        }

        planner_func = planner_map.get(query_type)
        if planner_func:
            planner_func(plan, parsed_query)
        else:
            logger.warning(f"Unknown query type: {query_type}")

        logger.info(
            "Execution plan created",
            tasks=len(plan.tasks),
            query_type=query_type,
            query=query_str[:50],
        )
        return plan

    # ================== New Blueprint Query Planners ==================

    def _plan_evaluate(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """
        Plan EVALUATE query execution

        EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY), TECHNICAL(RSI, MACD)

        Creates a DAG that:
        1. Fetches base price/OHLCV data
        2. Computes requested metrics in parallel
        3. Aggregates results
        """
        asset = parsed.get("asset", {})
        metrics = parsed.get("metrics", [])

        if not asset:
            return

        # Task 1: Fetch base price data
        price_task = ExecutionTask(
            type=TaskType.FETCH_PRICE,
            params={"asset": asset},
            priority=1,
            estimated_duration_ms=500,
        )
        price_id = plan.add_task(price_task)

        # Task 2: Fetch OHLCV for technical metrics
        ohlcv_task = ExecutionTask(
            type=TaskType.FETCH_OHLCV,
            params={"asset": asset, "timeframe": "1d", "limit": 100},
            priority=1,
            estimated_duration_ms=800,
        )
        ohlcv_id = plan.add_task(ohlcv_task)

        # Task 3+: Create tasks for each metric type
        compute_ids = []
        for metric in metrics:
            if not isinstance(metric, dict):
                continue

            category = metric.get("category", "")
            name = metric.get("name", "")

            if category == "technical" or name in ["volatility", "momentum"]:
                # Technical metrics depend on OHLCV
                task = ExecutionTask(
                    type=TaskType.COMPUTE_TECHNICAL,
                    params={"metric": metric, "asset": asset},
                    dependencies=[ohlcv_id],
                    priority=2,
                    estimated_duration_ms=300,
                )
                compute_ids.append(plan.add_task(task))

            elif category == "fundamental":
                # Fundamental metrics need separate fetch
                task = ExecutionTask(
                    type=TaskType.FETCH_FUNDAMENTALS,
                    params={"metric": metric, "asset": asset},
                    dependencies=[price_id],
                    priority=2,
                    estimated_duration_ms=600,
                )
                compute_ids.append(plan.add_task(task))

            elif category == "sentiment":
                # Sentiment needs news fetch + analysis
                task = ExecutionTask(
                    type=TaskType.COMPUTE_SENTIMENT,
                    params={"metric": metric, "asset": asset},
                    dependencies=[price_id],
                    priority=2,
                    estimated_duration_ms=800,
                )
                compute_ids.append(plan.add_task(task))

            elif category == "analysis" and name == "correlate":
                # Correlation analysis
                correlation_assets = metric.get("assets", [])
                task = ExecutionTask(
                    type=TaskType.COMPUTE_CORRELATION,
                    params={"primary_asset": asset, "correlation_assets": correlation_assets},
                    dependencies=[ohlcv_id],
                    priority=2,
                    estimated_duration_ms=500,
                )
                compute_ids.append(plan.add_task(task))

        # Final task: Aggregate all results
        if compute_ids:
            aggregate_task = ExecutionTask(
                type=TaskType.AGGREGATE,
                params={"query_type": "evaluate", "asset": asset, "metrics": metrics},
                dependencies=compute_ids,
                priority=3,
                estimated_duration_ms=100,
            )
            plan.add_task(aggregate_task)

    def _plan_macro(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """
        Plan MACRO query execution

        MACRO: US10Y, CPI, VIX → REGRESSION ON SPY

        Creates a DAG that:
        1. Fetches macro indicator data in parallel
        2. Fetches target asset data
        3. Performs regression/correlation analysis
        """
        indicators = parsed.get("indicators", [])
        analysis_type = parsed.get("analysis", "regression")
        target = parsed.get("target", {})

        if not indicators or not target:
            return

        # Task 1: Fetch macro indicators in parallel
        macro_ids = []
        for indicator in indicators:
            task = ExecutionTask(
                type=TaskType.FETCH_MACRO,
                params={"indicator": indicator},
                priority=1,
                estimated_duration_ms=400,
            )
            macro_ids.append(plan.add_task(task))

        # Task 2: Fetch target asset OHLCV
        target_task = ExecutionTask(
            type=TaskType.FETCH_OHLCV,
            params={"asset": target, "timeframe": "1d", "limit": 365},
            priority=1,
            estimated_duration_ms=800,
        )
        target_id = plan.add_task(target_task)

        # Task 3: Perform analysis
        if analysis_type == "regression":
            task_type = TaskType.COMPUTE_REGRESSION
        else:
            task_type = TaskType.COMPUTE_CORRELATION

        analysis_task = ExecutionTask(
            type=task_type,
            params={
                "indicators": indicators,
                "target": target,
                "analysis_type": analysis_type,
            },
            dependencies=macro_ids + [target_id],
            priority=2,
            estimated_duration_ms=1000,
        )
        plan.add_task(analysis_task)

    def _plan_correlate(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """
        Plan CORRELATE query execution

        CORRELATE TSLA WITH BTC, SPY WINDOW 90d

        Creates a DAG that:
        1. Fetches OHLCV for all assets in parallel
        2. Computes correlation matrix
        """
        primary_asset = parsed.get("asset", {})
        with_assets = parsed.get("with_assets", [])
        window = parsed.get("window")

        if not primary_asset or not with_assets:
            return

        # Determine lookback period from window
        lookback = 90  # default
        if window and isinstance(window, dict):
            value = window.get("value", 90)
            unit = window.get("unit", "d")
            if unit == "d":
                lookback = value
            elif unit == "w":
                lookback = value * 7
            elif unit == "m":
                lookback = value * 30

        # Task 1: Fetch primary asset OHLCV
        primary_task = ExecutionTask(
            type=TaskType.FETCH_OHLCV,
            params={"asset": primary_asset, "timeframe": "1d", "limit": lookback},
            priority=1,
            estimated_duration_ms=600,
        )
        primary_id = plan.add_task(primary_task)

        # Task 2: Fetch correlation assets OHLCV in parallel
        corr_ids = [primary_id]
        for asset in with_assets:
            task = ExecutionTask(
                type=TaskType.FETCH_OHLCV,
                params={"asset": asset, "timeframe": "1d", "limit": lookback},
                priority=1,
                estimated_duration_ms=600,
            )
            corr_ids.append(plan.add_task(task))

        # Task 3: Compute correlations
        correlation_task = ExecutionTask(
            type=TaskType.COMPUTE_CORRELATION,
            params={
                "primary_asset": primary_asset,
                "correlation_assets": with_assets,
                "window": window,
            },
            dependencies=corr_ids,
            priority=2,
            estimated_duration_ms=400,
        )
        plan.add_task(correlation_task)

    def _plan_scan(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """
        Plan SCAN query execution

        SCAN NASDAQ WHERE VOLUME > 1000000 AND PE < 20

        Creates a DAG that:
        1. Fetches market assets
        2. Applies filter conditions
        """
        market = parsed.get("market", "")
        conditions = parsed.get("conditions", [])

        if not market:
            return

        # Task 1: Scan market for assets
        scan_task = ExecutionTask(
            type=TaskType.SCAN_MARKET,
            params={"market": market, "conditions": conditions},
            priority=1,
            estimated_duration_ms=2000,
        )
        scan_id = plan.add_task(scan_task)

        # Task 2: Filter assets based on conditions
        filter_task = ExecutionTask(
            type=TaskType.FILTER_ASSETS,
            params={"conditions": conditions},
            dependencies=[scan_id],
            priority=2,
            estimated_duration_ms=500,
        )
        plan.add_task(filter_task)

    def _plan_track(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """
        Plan TRACK query execution

        TRACK AAPL WHEN PRICE > 150

        Creates a task to set up monitoring/alerts.
        """
        args = parsed.get("args", [])
        if len(args) < 2:
            return

        asset_spec = args[0]
        conditions = args[1]

        # Task: Set up monitoring
        track_task = ExecutionTask(
            type=TaskType.FILTER_ASSETS,
            params={"asset": asset_spec, "conditions": conditions, "mode": "track"},
            priority=1,
            estimated_duration_ms=100,
        )
        plan.add_task(track_task)

    # ================== Legacy Query Planners ==================

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

        elif analysis_type == "sentiment":
            sentiment_task = ExecutionTask(
                type=TaskType.COMPUTE_SENTIMENT,
                params={"asset": asset_spec},
                dependencies=[price_id],
                priority=2,
                estimated_duration_ms=800,
            )
            plan.add_task(sentiment_task)

        elif analysis_type == "correlations":
            corr_task = ExecutionTask(
                type=TaskType.COMPUTE_CORRELATION,
                params={"asset": asset_spec},
                dependencies=[ohlcv_id],
                priority=2,
                estimated_duration_ms=600,
            )
            plan.add_task(corr_task)

        elif analysis_type == "risk":
            risk_task = ExecutionTask(
                type=TaskType.COMPUTE_VOLATILITY,
                params={"asset": asset_spec},
                dependencies=[ohlcv_id],
                priority=2,
                estimated_duration_ms=400,
            )
            plan.add_task(risk_task)

    def _plan_compare(self, plan: ExecutionPlan, parsed: Dict[str, Any]) -> None:
        """Plan COMPARE query execution (both new and legacy syntax)"""
        # Handle new syntax: COMPARE BTC vs ETH ON: metrics
        if "assets" in parsed and "metrics" in parsed:
            assets = parsed["assets"]
            metrics = parsed["metrics"]
        # Handle legacy syntax: COMPARE AAPL, MSFT BY metrics
        else:
            args = parsed.get("args", [])
            if len(args) < 2:
                return
            assets = args[0] if isinstance(args[0], list) else [args[0]]
            metrics = args[1] if isinstance(args[1], list) else [args[1]]

        if not assets:
            return

        # Fetch data for each asset in parallel
        fetch_ids = []
        for asset in assets:
            # Determine what to fetch based on metrics
            has_fundamental = any(
                isinstance(m, dict) and m.get("category") == "fundamental" for m in metrics
            )

            if has_fundamental:
                task = ExecutionTask(
                    type=TaskType.FETCH_FUNDAMENTALS,
                    params={"asset": asset},
                    priority=1,
                    estimated_duration_ms=800,
                )
            else:
                task = ExecutionTask(
                    type=TaskType.FETCH_PRICE,
                    params={"asset": asset},
                    priority=1,
                    estimated_duration_ms=500,
                )
            fetch_ids.append(plan.add_task(task))

        # Compare metrics
        compare_task = ExecutionTask(
            type=TaskType.COMPARE_METRICS,
            params={"assets": assets, "metrics": metrics},
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

        data_request = args[0]
        if isinstance(data_request, dict):
            request_args = data_request.get("args", [])
        else:
            request_args = [data_request]

        # Determine task type from request
        if not request_args:
            task_type = TaskType.FETCH_PRICE
        else:
            first_arg = request_args[0] if request_args else ""
            if isinstance(first_arg, str):
                if first_arg.upper() == "OHLCV":
                    task_type = TaskType.FETCH_OHLCV
                elif first_arg.upper() == "FUNDAMENTALS":
                    task_type = TaskType.FETCH_FUNDAMENTALS
                elif first_arg.upper() == "NEWS":
                    task_type = TaskType.FETCH_NEWS
                else:
                    task_type = TaskType.FETCH_PRICE
            else:
                task_type = TaskType.FETCH_PRICE

        task = ExecutionTask(
            type=task_type,
            params={"data": request_args},
            priority=1,
            estimated_duration_ms=500,
        )
        plan.add_task(task)


# Global planner instance
execution_planner = ExecutionPlanner()
