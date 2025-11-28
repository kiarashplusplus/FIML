"""
Comprehensive tests for FK-DSL Parser, Planner, and Executor

Tests the complete DSL implementation including:
- New Blueprint-spec queries (EVALUATE, COMPARE, MACRO, CORRELATE, SCAN)
- Legacy queries (FIND, ANALYZE, TRACK, GET)
- Planner task generation
- Executor task execution
"""

import pytest

from fiml.core.models import TaskStatus
from fiml.dsl.executor import ExecutionTaskInfo, TaskExecutor, fk_dsl_executor
from fiml.dsl.parser import (AssetSpec, ConditionSpec, MetricSpec,
                             TimeframeSpec, fk_dsl_parser)
from fiml.dsl.planner import (ExecutionPlan, ExecutionTask, TaskType,
                              execution_planner)


class TestTimeframeSpec:
    """Test TimeframeSpec dataclass"""

    def test_timeframe_days(self):
        tf = TimeframeSpec(value=30, unit="d")
        assert tf.to_days() == 30
        assert str(tf) == "30d"

    def test_timeframe_hours(self):
        tf = TimeframeSpec(value=24, unit="h")
        assert tf.to_days() == 1.0
        assert str(tf) == "24h"

    def test_timeframe_weeks(self):
        tf = TimeframeSpec(value=4, unit="w")
        assert tf.to_days() == 28
        assert str(tf) == "4w"

    def test_timeframe_months(self):
        tf = TimeframeSpec(value=2, unit="m")
        assert tf.to_days() == 60
        assert str(tf) == "2m"

    def test_timeframe_years(self):
        tf = TimeframeSpec(value=1, unit="y")
        assert tf.to_days() == 365
        assert str(tf) == "1y"

    def test_timeframe_unknown_unit(self):
        tf = TimeframeSpec(value=10, unit="x")
        assert tf.to_days() == 10  # defaults to multiplier of 1


class TestMetricSpec:
    """Test MetricSpec dataclass"""

    def test_simple_metric(self):
        metric = MetricSpec(name="price", category="price")
        result = metric.to_dict()
        assert result["name"] == "price"
        assert result["category"] == "price"
        assert "params" not in result

    def test_metric_with_params(self):
        metric = MetricSpec(name="sma", category="technical", params=[20])
        result = metric.to_dict()
        assert result["params"] == [20]

    def test_metric_with_timeframe(self):
        tf = TimeframeSpec(value=30, unit="d")
        metric = MetricSpec(name="volatility", category="technical", timeframe=tf)
        result = metric.to_dict()
        assert result["timeframe"] == "30d"


class TestAssetSpec:
    """Test AssetSpec dataclass"""

    def test_simple_asset(self):
        asset = AssetSpec(symbol="AAPL")
        result = asset.to_dict()
        assert result["symbol"] == "AAPL"
        assert result["type"] == "symbol"
        assert "market" not in result

    def test_asset_with_market(self):
        asset = AssetSpec(symbol="AAPL", market="NASDAQ")
        result = asset.to_dict()
        assert result["market"] == "NASDAQ"


class TestConditionSpec:
    """Test ConditionSpec dataclass"""

    def test_simple_condition(self):
        cond = ConditionSpec(metric="PRICE", operator=">", value=100)
        result = cond.to_dict()
        assert result["operator"] == ">"
        assert result["value"] == 100

    def test_condition_with_metric_spec(self):
        metric = MetricSpec(name="rsi", category="technical")
        cond = ConditionSpec(metric=metric, operator="<", value=30)
        result = cond.to_dict()
        assert result["metric"]["name"] == "rsi"


class TestFKDSLParserEvaluate:
    """Test EVALUATE queries"""

    def test_evaluate_single_metric(self):
        query = "EVALUATE TSLA: PRICE"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "EVALUATE"
        assert result["asset"]["symbol"] == "TSLA"
        assert len(result["metrics"]) == 1

    def test_evaluate_multiple_metrics(self):
        query = "EVALUATE AAPL: PRICE, RSI, MACD"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "EVALUATE"
        assert len(result["metrics"]) == 3

    def test_evaluate_with_volatility(self):
        query = "EVALUATE TSLA: VOLATILITY(30d)"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "EVALUATE"
        metrics = result["metrics"]
        assert any(m.get("name") == "volatility" for m in metrics)

    def test_evaluate_with_volume_timeframe(self):
        query = "EVALUATE BTC: VOLUME(7d)"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "EVALUATE"

    def test_evaluate_with_momentum_timeframe(self):
        query = "EVALUATE ETH: MOMENTUM(14d)"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "EVALUATE"

    def test_evaluate_fundamental_metrics(self):
        query = "EVALUATE AAPL: PE, EPS, ROE"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "EVALUATE"
        metrics = result["metrics"]
        assert any(m.get("category") == "fundamental" for m in metrics)

    def test_evaluate_sentiment(self):
        query = "EVALUATE TSLA: SENTIMENT"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "EVALUATE"
        metrics = result["metrics"]
        assert any(m.get("name") == "sentiment" for m in metrics)

    def test_evaluate_liquidity(self):
        query = "EVALUATE BTC: LIQUIDITY"
        result = fk_dsl_parser.parse(query)
        metrics = result["metrics"]
        assert any(m.get("name") == "liquidity" for m in metrics)


class TestFKDSLParserCompare:
    """Test COMPARE queries"""

    def test_compare_new_syntax_two_assets(self):
        query = "COMPARE BTC vs ETH ON: VOLUME, LIQUIDITY"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "COMPARE"
        assert len(result["assets"]) == 2
        assert result["assets"][0]["symbol"] == "BTC"
        assert result["assets"][1]["symbol"] == "ETH"

    def test_compare_new_syntax_three_assets(self):
        query = "COMPARE BTC vs ETH vs SOL ON: VOLUME, MOMENTUM"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "COMPARE"
        assert len(result["assets"]) == 3

    def test_compare_legacy_syntax(self):
        query = "COMPARE AAPL, MSFT BY PE, EPS"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "COMPARE"
        assert "args" in result


class TestFKDSLParserMacro:
    """Test MACRO queries"""

    def test_macro_regression(self):
        query = "MACRO: US10Y, CPI, VIX -> REGRESSION ON SPY"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "MACRO"
        assert "US10Y" in result["indicators"]
        assert result["analysis"] == "regression"
        assert result["target"]["symbol"] == "SPY"

    def test_macro_correlation(self):
        query = "MACRO: VIX, DXY -> CORRELATION ON QQQ"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "MACRO"
        assert result["analysis"] == "correlation"

    def test_macro_with_arrow_symbol(self):
        query = "MACRO: GDP, UNEMPLOYMENT → IMPACT ON IWM"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "MACRO"
        assert result["analysis"] == "impact"

    def test_macro_single_indicator(self):
        query = "MACRO: FED_RATE -> CAUSALITY ON TLT"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "MACRO"
        assert len(result["indicators"]) == 1


class TestFKDSLParserCorrelate:
    """Test CORRELATE queries"""

    def test_correlate_basic(self):
        query = "CORRELATE TSLA WITH BTC, SPY"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "CORRELATE"
        assert result["asset"]["symbol"] == "TSLA"
        assert len(result["with_assets"]) == 2
        assert result["window"] is None

    def test_correlate_with_window(self):
        query = "CORRELATE AAPL WITH MSFT, GOOGL WINDOW 90d"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "CORRELATE"
        assert result["window"]["value"] == 90
        assert result["window"]["unit"] == "d"

    def test_correlate_single_asset(self):
        query = "CORRELATE BTC WITH ETH"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "CORRELATE"
        assert len(result["with_assets"]) == 1


class TestFKDSLParserScan:
    """Test SCAN queries"""

    def test_scan_simple(self):
        query = "SCAN NASDAQ WHERE VOLUME > 1000000"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "SCAN"
        assert result["market"] == "NASDAQ"
        assert len(result["conditions"]) == 1

    def test_scan_multiple_conditions(self):
        query = "SCAN NYSE WHERE VOLUME > 1000000 AND PE < 20"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "SCAN"
        assert len(result["conditions"]) == 2

    def test_scan_with_comparators(self):
        queries = [
            "SCAN NASDAQ WHERE RSI >= 70",
            "SCAN NASDAQ WHERE RSI <= 30",
            "SCAN NASDAQ WHERE PE != 0",
        ]
        for query in queries:
            result = fk_dsl_parser.parse(query)
            assert result["type"] == "SCAN"


class TestFKDSLParserLegacy:
    """Test legacy query types"""

    def test_find_query(self):
        query = "FIND AAPL WITH PRICE > 150 AND RSI < 30"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "FIND"

    def test_analyze_technicals(self):
        query = "ANALYZE AAPL FOR TECHNICALS"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "ANALYZE"
        assert result["args"][1] == "technicals"

    def test_analyze_fundamentals(self):
        query = "ANALYZE MSFT FOR FUNDAMENTALS"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "ANALYZE"
        assert result["args"][1] == "fundamentals"

    def test_analyze_sentiment(self):
        query = "ANALYZE TSLA FOR SENTIMENT"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "ANALYZE"
        assert result["args"][1] == "sentiment"

    def test_analyze_correlations(self):
        query = "ANALYZE NVDA FOR CORRELATIONS"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "ANALYZE"
        assert result["args"][1] == "correlations"

    def test_analyze_risk(self):
        query = "ANALYZE AMD FOR RISK"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "ANALYZE"
        assert result["args"][1] == "risk"

    def test_track_query(self):
        query = "TRACK AAPL WHEN PRICE > 200"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "TRACK"

    def test_get_price(self):
        query = "GET PRICE FOR AAPL"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "GET"

    def test_get_ohlcv(self):
        query = "GET OHLCV FOR BTCUSD 1d"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "GET"

    def test_get_news(self):
        query = "GET NEWS FOR TSLA"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "GET"

    def test_get_fundamentals(self):
        query = "GET FUNDAMENTALS FOR MSFT"
        result = fk_dsl_parser.parse(query)
        assert result["type"] == "GET"


class TestFKDSLParserValidation:
    """Test parser validation"""

    def test_validate_valid_queries(self):
        valid_queries = [
            "EVALUATE TSLA: PRICE",
            "COMPARE BTC vs ETH ON: VOLUME",
            "SCAN NASDAQ WHERE VOLUME > 100",
            "GET PRICE FOR AAPL",
        ]
        for query in valid_queries:
            assert fk_dsl_parser.validate(query) is True

    def test_validate_invalid_queries(self):
        invalid_queries = [
            "INVALID SYNTAX HERE",
            "FOOBAR TSLA PRICE",
            "",
            "SELECT * FROM assets",
        ]
        for query in invalid_queries:
            assert fk_dsl_parser.validate(query) is False


class TestFKDSLParserMetrics:
    """Test metric parsing"""

    def test_technical_indicators_sma(self):
        query = "EVALUATE AAPL: SMA 20"
        result = fk_dsl_parser.parse(query)
        metrics = result["metrics"]
        assert any(m.get("name") == "sma" and m.get("period") == 20 for m in metrics)

    def test_technical_indicators_ema(self):
        query = "EVALUATE AAPL: EMA 50"
        result = fk_dsl_parser.parse(query)
        metrics = result["metrics"]
        assert any(m.get("name") == "ema" and m.get("period") == 50 for m in metrics)

    def test_stoch_metric(self):
        query = "EVALUATE AAPL: STOCH"
        result = fk_dsl_parser.parse(query)
        metrics = result["metrics"]
        assert any(m.get("name") == "stoch" for m in metrics)

    def test_atr_metric(self):
        query = "EVALUATE AAPL: ATR"
        result = fk_dsl_parser.parse(query)
        metrics = result["metrics"]
        assert any(m.get("name") == "atr" for m in metrics)

    def test_buzz_metric(self):
        query = "EVALUATE TSLA: BUZZ"
        result = fk_dsl_parser.parse(query)
        metrics = result["metrics"]
        assert any(m.get("name") == "buzz" for m in metrics)

    def test_news_score_metric(self):
        query = "EVALUATE AAPL: NEWS_SCORE"
        result = fk_dsl_parser.parse(query)
        metrics = result["metrics"]
        assert any(m.get("name") == "news_score" for m in metrics)


class TestExecutionPlannerEvaluate:
    """Test planner for EVALUATE queries"""

    def test_plan_evaluate_simple(self):
        query = "EVALUATE TSLA: PRICE"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan.query_type == "EVALUATE"
        assert len(plan.tasks) >= 2  # At least price and OHLCV fetch

    def test_plan_evaluate_with_technicals(self):
        query = "EVALUATE AAPL: PRICE, RSI, MACD"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        # Should have technical compute tasks
        technical_tasks = [t for t in plan.tasks if t.type == TaskType.COMPUTE_TECHNICAL]
        assert len(technical_tasks) >= 1

    def test_plan_evaluate_with_fundamentals(self):
        query = "EVALUATE MSFT: PE, EPS"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        # Should have fundamentals fetch tasks
        fundamental_tasks = [t for t in plan.tasks if t.type == TaskType.FETCH_FUNDAMENTALS]
        assert len(fundamental_tasks) >= 1


class TestExecutionPlannerMacro:
    """Test planner for MACRO queries"""

    def test_plan_macro_regression(self):
        query = "MACRO: US10Y, CPI -> REGRESSION ON SPY"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan.query_type == "MACRO"
        # Should have macro fetch tasks
        macro_tasks = [t for t in plan.tasks if t.type == TaskType.FETCH_MACRO]
        assert len(macro_tasks) == 2  # One for each indicator


class TestExecutionPlannerCorrelate:
    """Test planner for CORRELATE queries"""

    def test_plan_correlate(self):
        query = "CORRELATE TSLA WITH BTC, SPY WINDOW 90d"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan.query_type == "CORRELATE"
        # Should have OHLCV fetch tasks and correlation task
        ohlcv_tasks = [t for t in plan.tasks if t.type == TaskType.FETCH_OHLCV]
        assert len(ohlcv_tasks) == 3  # Primary + 2 correlation assets


class TestExecutionPlannerScan:
    """Test planner for SCAN queries"""

    def test_plan_scan(self):
        query = "SCAN NASDAQ WHERE VOLUME > 1000000"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan.query_type == "SCAN"
        # Should have scan and filter tasks
        scan_tasks = [t for t in plan.tasks if t.type == TaskType.SCAN_MARKET]
        assert len(scan_tasks) == 1


class TestExecutionPlannerLegacy:
    """Test planner for legacy queries"""

    def test_plan_track(self):
        query = "TRACK AAPL WHEN PRICE > 200"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan.query_type == "TRACK"

    def test_plan_analyze_sentiment(self):
        query = "ANALYZE TSLA FOR SENTIMENT"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        sentiment_tasks = [t for t in plan.tasks if t.type == TaskType.COMPUTE_SENTIMENT]
        assert len(sentiment_tasks) == 1

    def test_plan_analyze_correlations(self):
        query = "ANALYZE NVDA FOR CORRELATIONS"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        correlation_tasks = [t for t in plan.tasks if t.type == TaskType.COMPUTE_CORRELATION]
        assert len(correlation_tasks) == 1

    def test_plan_analyze_risk(self):
        query = "ANALYZE AMD FOR RISK"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        volatility_tasks = [t for t in plan.tasks if t.type == TaskType.COMPUTE_VOLATILITY]
        assert len(volatility_tasks) == 1


class TestExecutionPlan:
    """Test ExecutionPlan class"""

    def test_get_estimated_duration(self):
        plan = ExecutionPlan(query="test")

        # Add tasks with dependencies
        task1 = ExecutionTask(type=TaskType.FETCH_PRICE, estimated_duration_ms=500)
        task1_id = plan.add_task(task1)

        task2 = ExecutionTask(
            type=TaskType.COMPUTE_TECHNICAL, dependencies=[task1_id], estimated_duration_ms=300
        )
        plan.add_task(task2)

        # Duration should be critical path (500 + 300 = 800)
        assert plan.get_estimated_duration_ms() == 800

    def test_get_estimated_duration_parallel(self):
        plan = ExecutionPlan(query="test")

        # Add parallel tasks
        task1 = ExecutionTask(type=TaskType.FETCH_PRICE, estimated_duration_ms=500)
        task2 = ExecutionTask(type=TaskType.FETCH_OHLCV, estimated_duration_ms=800)
        plan.add_task(task1)
        plan.add_task(task2)

        # Duration should be max of parallel tasks
        assert plan.get_estimated_duration_ms() == 800

    def test_to_dict_includes_duration(self):
        plan = ExecutionPlan(query="test", query_type="EVALUATE")
        task = ExecutionTask(type=TaskType.FETCH_PRICE, estimated_duration_ms=500)
        plan.add_task(task)

        result = plan.to_dict()
        assert "estimated_total_duration_ms" in result
        assert result["query_type"] == "EVALUATE"


class TestTaskExecutorNewTypes:
    """Test TaskExecutor with new task types"""

    @pytest.mark.asyncio
    async def test_fetch_macro(self):
        executor = TaskExecutor()
        task = ExecutionTask(type=TaskType.FETCH_MACRO, params={"indicator": "US10Y"})
        result = await executor.execute(task, {})
        assert result is not None
        assert "value" in result

    @pytest.mark.asyncio
    async def test_compute_volatility(self):
        executor = TaskExecutor()
        task = ExecutionTask(type=TaskType.COMPUTE_VOLATILITY, params={"asset": {"symbol": "AAPL"}})
        result = await executor.execute(task, {})
        assert result is not None
        assert "historical_volatility" in result

    @pytest.mark.asyncio
    async def test_compute_correlation(self):
        executor = TaskExecutor()
        task = ExecutionTask(
            type=TaskType.COMPUTE_CORRELATION,
            params={"primary_asset": {"symbol": "TSLA"}, "correlation_assets": [{"symbol": "SPY"}]},
        )
        result = await executor.execute(task, {})
        assert result is not None
        assert "correlations" in result

    @pytest.mark.asyncio
    async def test_compute_regression(self):
        executor = TaskExecutor()
        task = ExecutionTask(
            type=TaskType.COMPUTE_REGRESSION,
            params={
                "indicators": ["US10Y", "VIX"],
                "target": {"symbol": "SPY"},
                "analysis_type": "regression",
            },
        )
        result = await executor.execute(task, {})
        assert result is not None
        assert "r_squared" in result

    @pytest.mark.asyncio
    async def test_scan_market(self):
        executor = TaskExecutor()
        task = ExecutionTask(
            type=TaskType.SCAN_MARKET, params={"market": "NASDAQ", "conditions": []}
        )
        result = await executor.execute(task, {})
        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_aggregate(self):
        executor = TaskExecutor()
        task = ExecutionTask(
            type=TaskType.AGGREGATE,
            params={"query_type": "evaluate", "asset": {"symbol": "AAPL"}, "metrics": []},
            dependencies=[],
        )
        result = await executor.execute(task, {})
        assert result is not None
        assert "query_type" in result

    @pytest.mark.asyncio
    async def test_generate_narrative(self):
        executor = TaskExecutor()
        task = ExecutionTask(type=TaskType.GENERATE_NARRATIVE, params={})
        result = await executor.execute(task, {})
        assert result is not None
        assert "summary" in result


class TestFKDSLExecutorIntegration:
    """Integration tests for full query execution"""

    @pytest.mark.asyncio
    async def test_execute_evaluate_query(self):
        query = "EVALUATE AAPL: PRICE, RSI"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        result = await fk_dsl_executor.execute_sync(plan)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_scan_query(self):
        query = "SCAN NASDAQ WHERE VOLUME > 1000000"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        result = await fk_dsl_executor.execute_sync(plan)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_macro_query(self):
        query = "MACRO: US10Y, VIX -> REGRESSION ON SPY"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        result = await fk_dsl_executor.execute_sync(plan)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_correlate_query(self):
        query = "CORRELATE TSLA WITH BTC, SPY WINDOW 30d"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        result = await fk_dsl_executor.execute_sync(plan)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_task_status_with_query_type(self):
        query = "EVALUATE AAPL: PRICE"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        task_id = await fk_dsl_executor.execute_async(plan)

        # Wait briefly for task to start
        import asyncio

        await asyncio.sleep(0.1)

        status = fk_dsl_executor.get_task_status(task_id)
        assert status is not None
        assert "dsl_" in status.type


class TestExecutionTaskInfo:
    """Test ExecutionTaskInfo model"""

    def test_with_query_type(self):
        info = ExecutionTaskInfo(
            task_id="test-123",
            status=TaskStatus.RUNNING,
            query="EVALUATE AAPL: PRICE",
            query_type="EVALUATE",
            total_steps=5,
        )
        assert info.query_type == "EVALUATE"
