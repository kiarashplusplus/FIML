"""
Additional tests for DSL components
"""

import pytest

from fiml.dsl.executor import fk_dsl_executor
from fiml.dsl.parser import fk_dsl_parser
from fiml.dsl.planner import ExecutionTask, TaskType, execution_planner


class TestDSLParserAdvanced:
    """Advanced DSL parser tests"""

    def test_parse_track_query(self):
        """Test parsing TRACK query"""
        query = "TRACK AAPL WHEN PRICE > 150"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None
        assert parsed["type"] == "TRACK"

    def test_parse_with_market(self):
        """Test parsing with market specification"""
        query = "GET PRICE FOR AAPL"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None
        assert parsed["type"] == "GET"

    def test_parse_technical_indicators(self):
        """Test parsing queries with technical indicators"""
        query = "FIND AAPL WITH RSI < 30"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None
        assert "args" in parsed

    def test_validate_valid_query(self):
        """Test validating a valid query"""
        query = "GET PRICE FOR AAPL"
        assert fk_dsl_parser.validate(query) is True

    def test_validate_invalid_query(self):
        """Test validating an invalid query"""
        query = "INVALID SYNTAX HERE"
        assert fk_dsl_parser.validate(query) is False

    def test_multiple_conditions(self):
        """Test parsing multiple conditions"""
        query = "FIND AAPL WITH PRICE > 150 AND VOLUME > 1000000"
        parsed = fk_dsl_parser.parse(query)

        assert parsed is not None
        # Should have multiple conditions
        conditions = parsed["args"][1]
        assert isinstance(conditions, list)


class TestExecutionPlannerAdvanced:
    """Advanced execution planner tests"""

    def test_plan_compare_query(self):
        """Test planning COMPARE query"""
        query = "COMPARE AAPL, MSFT BY PE, EPS"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan is not None
        assert plan.query == query

    def test_plan_track_query(self):
        """Test planning TRACK query"""
        query = "TRACK AAPL WHEN PRICE > 150"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        assert plan is not None
        # Even if no tasks are created, plan should exist
        assert plan.query == query

    def test_execution_plan_add_task(self):
        """Test adding tasks to execution plan"""
        from fiml.dsl.planner import ExecutionPlan

        plan = ExecutionPlan(query="test")

        task = ExecutionTask(
            type=TaskType.FETCH_PRICE,
            params={"symbol": "AAPL"}
        )

        task_id = plan.add_task(task)
        assert task_id is not None
        assert len(plan.tasks) == 1
        assert task_id in plan.root_task_ids

    def test_execution_plan_get_task(self):
        """Test getting task from plan"""
        from fiml.dsl.planner import ExecutionPlan

        plan = ExecutionPlan(query="test")

        task = ExecutionTask(
            type=TaskType.FETCH_PRICE,
            params={"symbol": "AAPL"}
        )

        task_id = plan.add_task(task)
        retrieved = plan.get_task(task_id)

        assert retrieved is not None
        assert retrieved.id == task_id

    def test_execution_plan_get_executable_tasks(self):
        """Test getting executable tasks"""
        from fiml.dsl.planner import ExecutionPlan

        plan = ExecutionPlan(query="test")

        # Add tasks with dependencies
        task1 = ExecutionTask(type=TaskType.FETCH_PRICE)
        task1_id = plan.add_task(task1)

        task2 = ExecutionTask(
            type=TaskType.COMPUTE_TECHNICAL,
            dependencies=[task1_id]
        )
        plan.add_task(task2)

        # Initially, only task1 is executable
        executable = plan.get_executable_tasks(set())
        assert len(executable) == 1
        assert executable[0].id == task1_id

        # After task1 completes, task2 is executable
        executable = plan.get_executable_tasks({task1_id})
        assert len(executable) == 1

    def test_execution_plan_to_dict(self):
        """Test converting plan to dict"""
        from fiml.dsl.planner import ExecutionPlan

        plan = ExecutionPlan(query="test")
        task = ExecutionTask(type=TaskType.FETCH_PRICE)
        plan.add_task(task)

        plan_dict = plan.to_dict()
        assert "query" in plan_dict
        assert "tasks" in plan_dict


class TestDSLExecutorAdvanced:
    """Advanced DSL executor tests"""

    @pytest.mark.asyncio
    async def test_execute_empty_plan(self):
        """Test executing an empty plan"""
        from fiml.dsl.planner import ExecutionPlan

        plan = ExecutionPlan(query="test")

        # Execute empty plan
        result = await fk_dsl_executor.execute_sync(plan)

        # Should complete without errors
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_task_status_nonexistent(self):
        """Test getting status of nonexistent task"""
        status = fk_dsl_executor.get_task_status("nonexistent-task-id")
        assert status is None

    @pytest.mark.asyncio
    async def test_execute_simple_get_query(self):
        """Test executing a simple GET query"""
        query = "GET PRICE FOR AAPL"
        parsed = fk_dsl_parser.parse(query)
        plan = execution_planner.plan(parsed, query)

        # Execute the plan
        result = await fk_dsl_executor.execute_sync(plan)

        # Should return a result
        assert result is not None
