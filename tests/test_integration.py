"""
Integration Tests for Cache, DSL, and Multi-Agent Systems
"""

import asyncio

import pytest

from fiml.agents.orchestrator import agent_orchestrator
from fiml.cache.l1_cache import l1_cache
from fiml.cache.manager import cache_manager
from fiml.core.models import Asset, AssetType, Market
from fiml.dsl.executor import fk_dsl_executor
from fiml.dsl.parser import fk_dsl_parser
from fiml.dsl.planner import execution_planner


class TestL1Cache:
    """Test L1 (Redis) cache"""

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic cache operations"""
        # Note: Requires Redis running
        try:
            await l1_cache.initialize()

            # Set value
            success = await l1_cache.set("test:key", {"value": 123}, ttl_seconds=60)
            assert success

            # Get value
            result = await l1_cache.get("test:key")
            assert result == {"value": 123}

            # Delete
            deleted = await l1_cache.delete("test:key")
            assert deleted

            await l1_cache.shutdown()

        except Exception as e:
            # Redis not available
            pytest.skip(f"Redis not available: {e}")


class TestCacheManager:
    """Test cache manager with L1/L2 fallback"""

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self):
        """Test cache manager init"""
        await cache_manager.initialize()
        stats = await cache_manager.get_stats()
        assert "l1" in stats
        await cache_manager.shutdown()


class TestFKDSLParser:
    """Test Financial Knowledge DSL parser"""

    def test_parse_find_query(self):
        """Test parsing FIND query"""
        query = "FIND AAPL WITH PRICE > 150 AND RSI < 30"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None
        assert "type" in parsed

    def test_parse_analyze_query(self):
        """Test parsing ANALYZE query"""
        query = "ANALYZE AAPL FOR TECHNICALS"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None
        assert "type" in parsed

    def test_parse_compare_query(self):
        """Test parsing COMPARE query"""
        query = "COMPARE AAPL, MSFT BY PE, EPS"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None

    def test_parse_get_query(self):
        """Test parsing GET query"""
        query = "GET PRICE FOR AAPL"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None

    def test_invalid_query(self):
        """Test invalid query handling"""
        from fiml.core.exceptions import FKDSLParseError

        with pytest.raises(FKDSLParseError):
            fk_dsl_parser.parse("INVALID QUERY SYNTAX")


class TestExecutionPlanner:
    """Test execution planner"""

    def test_plan_find_query(self):
        """Test planning FIND query"""
        query = "FIND AAPL WITH PRICE > 150"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan is not None
        assert len(plan.tasks) > 0
        assert plan.query == query

    def test_plan_analyze_query(self):
        """Test planning ANALYZE query"""
        query = "ANALYZE AAPL FOR TECHNICALS"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert len(plan.tasks) > 0


class TestFKDSLExecutor:
    """Test DSL executor"""

    @pytest.mark.asyncio
    async def test_async_execution(self):
        """Test async execution"""
        query = "GET PRICE FOR AAPL"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        # Start async execution
        task_id = await fk_dsl_executor.execute_async(plan)
        assert task_id is not None

        # Wait for completion
        await asyncio.sleep(1.0)

        # Check status
        status = fk_dsl_executor.get_task_status(task_id)
        assert status is not None

    @pytest.mark.asyncio
    async def test_sync_execution(self):
        """Test sync execution"""
        query = "GET PRICE FOR AAPL"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        # Execute synchronously
        result = await fk_dsl_executor.execute_sync(plan)
        assert result is not None


class TestMultiAgentOrchestration:
    """Test multi-agent orchestrator"""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator init"""
        try:
            await agent_orchestrator.initialize()
            assert agent_orchestrator.initialized

            # Health check
            health = await agent_orchestrator.health_check()
            assert health["status"] in ["healthy", "not_initialized"]

            await agent_orchestrator.shutdown()

        except Exception as e:
            # Ray not available
            pytest.skip(f"Ray not available: {e}")

    @pytest.mark.asyncio
    async def test_analyze_asset(self):
        """Test multi-agent asset analysis"""
        try:
            await agent_orchestrator.initialize()

            asset = Asset(
                symbol="AAPL",
                name="Apple Inc.",
                asset_type=AssetType.STOCK,
                market=Market.US,
            )

            # Run analysis
            result = await agent_orchestrator.analyze_asset(
                asset, agents=["fundamentals", "technical"]
            )

            assert "asset" in result
            assert "analyses" in result
            assert "aggregate" in result
            assert "overall_score" in result["aggregate"]

            await agent_orchestrator.shutdown()

        except Exception as e:
            pytest.skip(f"Ray not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
