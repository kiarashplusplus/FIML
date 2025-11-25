"""
FK-DSL Executor - Executes planned tasks

Implements the execution engine for FK-DSL queries, supporting:
- Parallel task execution via DAG-based scheduling
- New Blueprint task types (macro, correlation, volatility, etc.)
- Legacy task types (fetch, compute, filter, compare)
- Progress tracking and result aggregation
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
    query_type: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_steps: int = 0
    completed_steps: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskExecutor:
    """
    Executes individual tasks in the execution plan.

    Supports all task types from TaskType enum, including:
    - Data fetching (price, OHLCV, fundamentals, news, macro)
    - Computation (technical, sentiment, volatility, correlation, regression)
    - Analysis (filter, compare, scan, aggregate)
    """

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

        # Map task types to handlers
        handlers = {
            TaskType.FETCH_PRICE: self._fetch_price,
            TaskType.FETCH_OHLCV: self._fetch_ohlcv,
            TaskType.FETCH_FUNDAMENTALS: self._fetch_fundamentals,
            TaskType.FETCH_NEWS: self._fetch_news,
            TaskType.FETCH_MACRO: self._fetch_macro,
            TaskType.COMPUTE_TECHNICAL: self._compute_technical,
            TaskType.COMPUTE_SENTIMENT: self._compute_sentiment,
            TaskType.COMPUTE_VOLATILITY: self._compute_volatility,
            TaskType.COMPUTE_CORRELATION: self._compute_correlation,
            TaskType.COMPUTE_REGRESSION: self._compute_regression,
            TaskType.FILTER_ASSETS: self._filter_assets,
            TaskType.COMPARE_METRICS: self._compare_metrics,
            TaskType.SCAN_MARKET: self._scan_market,
            TaskType.AGGREGATE: self._aggregate,
            TaskType.GENERATE_NARRATIVE: self._generate_narrative,
        }

        handler = handlers.get(task.type)
        if handler is None:
            logger.warning(f"Unknown task type: {task.type}")
            return None

        try:
            return await handler(task, context)
        except Exception as e:
            logger.error(f"Task execution failed: {e}", task_id=task.id)
            raise FKDSLExecutionError(f"Task {task.id} failed: {e}")

    # ================== Data Fetching Tasks ==================

    async def _fetch_price(self, task: ExecutionTask, context: Dict) -> Dict[str, Any]:
        """Fetch current price data for an asset"""
        await asyncio.sleep(0.1)  # Simulated API call

        asset = task.params.get("asset", {})
        symbol = asset.get("symbol", "UNKNOWN") if isinstance(asset, dict) else str(asset)

        return {
            "symbol": symbol,
            "price": 150.25,
            "change": 2.5,
            "change_percent": 1.69,
            "volume": 50000000,
            "market_cap": 2500000000000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _fetch_ohlcv(self, task: ExecutionTask, context: Dict) -> List[Dict]:
        """Fetch OHLCV (candlestick) data"""
        await asyncio.sleep(0.2)

        # Use asset for logging if needed in production
        _ = task.params.get("asset", {})
        limit = task.params.get("limit", 100)

        # Generate mock OHLCV data
        data = []
        base_price = 150.0
        for i in range(min(limit, 10)):  # Mock data limited for testing
            data.append({
                "time": f"2024-01-{i + 1:02d}",
                "open": base_price + i,
                "high": base_price + i + 5,
                "low": base_price + i - 3,
                "close": base_price + i + 2,
                "volume": 1000000 + i * 100000,
            })

        return data

    async def _fetch_fundamentals(self, task: ExecutionTask, context: Dict) -> Dict:
        """Fetch fundamental data (PE, EPS, etc.)"""
        await asyncio.sleep(0.3)

        return {
            "pe_ratio": 25.5,
            "eps": 6.12,
            "market_cap": 2500000000000,
            "revenue": 380000000000,
            "profit_margin": 0.24,
            "roe": 0.45,
            "debt_to_equity": 1.5,
            "dividend_yield": 0.005,
        }

    async def _fetch_news(self, task: ExecutionTask, context: Dict) -> List[Dict]:
        """Fetch news articles"""
        await asyncio.sleep(0.15)

        return [
            {
                "title": "Company announces strong earnings",
                "sentiment": 0.8,
                "source": "Financial Times",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "title": "New product launch expected",
                "sentiment": 0.6,
                "source": "Reuters",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

    async def _fetch_macro(self, task: ExecutionTask, context: Dict) -> Dict[str, Any]:
        """Fetch macroeconomic indicator data"""
        await asyncio.sleep(0.2)

        indicator = task.params.get("indicator", "")

        # Mock macro data for common indicators
        macro_data = {
            "US10Y": {"value": 4.25, "change": 0.05, "unit": "percent"},
            "CPI": {"value": 3.2, "change": -0.1, "unit": "percent"},
            "VIX": {"value": 18.5, "change": 1.2, "unit": "index"},
            "DXY": {"value": 102.5, "change": 0.3, "unit": "index"},
            "UNEMPLOYMENT": {"value": 3.8, "change": 0.0, "unit": "percent"},
            "GDP": {"value": 2.1, "change": 0.2, "unit": "percent"},
            "FED_RATE": {"value": 5.25, "change": 0.0, "unit": "percent"},
        }

        return macro_data.get(indicator, {"value": 0, "change": 0, "unit": "unknown"})

    # ================== Computation Tasks ==================

    async def _compute_technical(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compute technical indicators (RSI, MACD, etc.)"""
        await asyncio.sleep(0.1)

        metric = task.params.get("metric", {})
        indicators = task.params.get("indicators", [])

        result = {}

        # RSI
        if "RSI" in indicators or metric.get("name") == "rsi":
            result["rsi"] = {
                "value": 45.2,
                "signal": "neutral",
                "overbought": False,
                "oversold": False,
            }

        # MACD
        if "MACD" in indicators or metric.get("name") == "macd":
            result["macd"] = {
                "macd": 1.2,
                "signal": 0.8,
                "histogram": 0.4,
                "crossover": "bullish",
            }

        # SMA/EMA
        if "SMA" in indicators or metric.get("name") == "sma":
            result["sma"] = {"value": 148.5, "period": metric.get("period", 20)}

        if "EMA" in indicators or metric.get("name") == "ema":
            result["ema"] = {"value": 149.2, "period": metric.get("period", 20)}

        # Volatility (if requested as technical)
        if metric.get("name") == "volatility":
            timeframe = metric.get("timeframe", {})
            result["volatility"] = {
                "value": 0.42,
                "annualized": 0.78,
                "period": f"{timeframe.get('value', 30)}{timeframe.get('unit', 'd')}",
            }

        # Momentum
        if metric.get("name") == "momentum":
            result["momentum"] = {"value": 2.5, "direction": "positive"}

        return result

    async def _compute_sentiment(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compute sentiment analysis from news/social data"""
        await asyncio.sleep(0.15)

        return {
            "overall": 0.65,
            "news_sentiment": 0.72,
            "social_sentiment": 0.58,
            "trend": "positive",
            "sample_size": 150,
        }

    async def _compute_volatility(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compute volatility metrics"""
        await asyncio.sleep(0.1)

        return {
            "historical_volatility": 0.35,
            "implied_volatility": 0.42,
            "atr": 5.2,
            "beta": 1.15,
        }

    async def _compute_correlation(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compute correlation between assets"""
        await asyncio.sleep(0.2)

        primary = task.params.get("primary_asset", {})
        correlation_assets = task.params.get("correlation_assets", [])
        window = task.params.get("window", {})

        correlations = {}
        for asset in correlation_assets:
            symbol = asset.get("symbol", str(asset)) if isinstance(asset, dict) else str(asset)
            # Mock correlation values
            correlations[symbol] = {
                "coefficient": 0.65 if symbol == "SPY" else 0.35,
                "p_value": 0.001,
                "strength": "strong" if symbol == "SPY" else "moderate",
            }

        return {
            "primary_asset": primary,
            "correlations": correlations,
            "window": window,
        }

    async def _compute_regression(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compute regression analysis"""
        await asyncio.sleep(0.3)

        indicators = task.params.get("indicators", [])
        target = task.params.get("target", {})
        analysis_type = task.params.get("analysis_type", "regression")

        # Mock regression results
        coefficients = {}
        p_values = {}
        for indicator in indicators:
            coefficients[indicator] = -0.42 if indicator == "US10Y" else -0.25
            p_values[indicator] = 0.001 if indicator in ["US10Y", "VIX"] else 0.05

        return {
            "r_squared": 0.73,
            "coefficients": coefficients,
            "p_values": p_values,
            "analysis_type": analysis_type,
            "target": target,
        }

    # ================== Analysis Tasks ==================

    async def _filter_assets(self, task: ExecutionTask, context: Dict) -> List[Dict]:
        """Filter assets by conditions"""
        await asyncio.sleep(0.05)

        conditions = task.params.get("conditions", [])
        # Mode can be 'filter' or 'track' - used for logging/behavior in production
        _ = task.params.get("mode", "filter")

        return [
            {"symbol": "AAPL", "matches": True, "conditions_met": len(conditions)},
            {"symbol": "MSFT", "matches": True, "conditions_met": len(conditions)},
        ]

    async def _compare_metrics(self, task: ExecutionTask, context: Dict) -> Dict:
        """Compare metrics across multiple assets"""
        await asyncio.sleep(0.05)

        assets = task.params.get("assets", [])
        metrics = task.params.get("metrics", [])

        comparison = []
        for asset in assets:
            symbol = asset.get("symbol", str(asset)) if isinstance(asset, dict) else str(asset)
            comparison.append({
                "asset": symbol,
                "pe": 25.5 if symbol == "AAPL" else 30.2,
                "eps": 6.12 if symbol == "AAPL" else 8.45,
            })

        return {"comparison": comparison, "metrics": metrics}

    async def _scan_market(self, task: ExecutionTask, context: Dict) -> List[Dict]:
        """Scan market for assets matching conditions"""
        await asyncio.sleep(0.5)

        market = task.params.get("market", "")
        # Conditions would be applied in production filtering
        _ = task.params.get("conditions", [])

        # Mock market scan results
        return [
            {"symbol": "NVDA", "market": market, "volume": 150000000, "change": 5.2},
            {"symbol": "AMD", "market": market, "volume": 80000000, "change": 3.8},
            {"symbol": "TSLA", "market": market, "volume": 120000000, "change": 6.1},
        ]

    async def _aggregate(self, task: ExecutionTask, context: Dict) -> Dict:
        """Aggregate results from multiple tasks"""
        await asyncio.sleep(0.05)

        query_type = task.params.get("query_type", "")
        asset = task.params.get("asset", {})
        metrics = task.params.get("metrics", [])

        # Aggregate results from context
        aggregated = {
            "query_type": query_type,
            "asset": asset,
            "metrics_computed": len(metrics),
            "results": {},
        }

        # Pull results from dependency context
        for dep_id in task.dependencies:
            if dep_id in context:
                aggregated["results"][dep_id] = context[dep_id]

        return aggregated

    async def _generate_narrative(self, task: ExecutionTask, context: Dict) -> Dict:
        """Generate narrative summary from analysis results"""
        await asyncio.sleep(0.1)

        return {
            "summary": "Analysis complete. Asset shows moderate momentum with neutral RSI.",
            "key_insights": [
                "RSI indicates neutral conditions",
                "MACD shows bullish crossover",
                "Correlation with market index is strong",
            ],
            "risk_factors": [
                "High volatility in the 75th percentile",
            ],
        }


class FKDSLExecutor:
    """
    Executes FK-DSL queries using DAG-based execution

    Features:
    - Parallel task execution with dependency management
    - Progress tracking with real-time status updates
    - Result caching for repeated queries
    - Support for async and sync execution modes
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
            query_type=plan.query_type,
            total_steps=len(plan.tasks),
            completed_steps=0,
        )

        self.active_executions[task_id] = task_info

        # Execute in background
        asyncio.create_task(self._execute_plan(task_id, plan))

        logger.info(
            "Async execution started",
            task_id=task_id,
            query_type=plan.query_type,
            query=plan.query[:50],
        )
        return task_id

    async def _execute_plan(self, task_id: str, plan: ExecutionPlan) -> None:
        """Execute plan DAG with parallel task scheduling"""
        task_info = self.active_executions[task_id]
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.now(timezone.utc)

        completed: Set[str] = set()
        results: Dict[str, Any] = {}
        context: Dict[str, Any] = {}

        try:
            # Execute tasks in dependency order
            while len(completed) < len(plan.tasks):
                # Get executable tasks (all dependencies satisfied)
                executable = plan.get_executable_tasks(completed)

                if not executable:
                    if len(completed) < len(plan.tasks):
                        raise FKDSLExecutionError("Circular dependency detected")
                    break

                # Execute in parallel
                tasks = [
                    self.task_executor.execute(task, context) for task in executable
                ]

                task_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Store results and update context
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

            logger.info(
                "Execution completed",
                task_id=task_id,
                tasks_completed=len(completed),
            )

        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error = str(e)
            task_info.completed_at = datetime.now(timezone.utc)
            logger.error(f"Execution failed: {e}", task_id=task_id)

    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get execution status for a task"""
        internal_info = self.active_executions.get(task_id)
        if internal_info is None:
            return None

        # Convert internal info to TaskInfo
        return TaskInfo(
            id=internal_info.task_id,
            type=f"dsl_{internal_info.query_type.lower()}" if internal_info.query_type else "dsl_execution",
            status=internal_info.status,
            resource_url=f"/api/tasks/{task_id}",
            progress=(
                internal_info.completed_steps / max(internal_info.total_steps, 1)
                if internal_info.total_steps > 0
                else 0.0
            ),
            created_at=internal_info.created_at,
            updated_at=internal_info.completed_at
            or internal_info.started_at
            or internal_info.created_at,
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
            if internal_info and internal_info.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
            ]:
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
