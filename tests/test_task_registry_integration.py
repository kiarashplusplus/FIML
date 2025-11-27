"""
Integration tests for Redis-backed TaskRegistry using real Docker Redis on port 6380
"""

from datetime import datetime, timezone

import pytest
import redis

from fiml.core.models import TaskInfo, TaskStatus
from fiml.monitoring.task_registry import TaskRegistry


@pytest.fixture
def redis_client():
    """Connect to the real Docker Redis on port 6380"""
    client = redis.Redis(host="localhost", port=6380, db=0, decode_responses=False)
    # Test connection
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis not available on port 6380")

    yield client

    # Cleanup all test keys
    for key in client.scan_iter("fiml:task:test_*"):
        client.delete(key)
    client.close()


@pytest.fixture
def task_registry(redis_client):
    """TaskRegistry using real Redis"""
    registry = TaskRegistry()
    # Override the lazy connection to use our test Redis
    registry._redis_client = redis_client
    return registry


@pytest.fixture
def sample_task():
    """Sample task for testing"""
    return TaskInfo(
        id="test_task_001",
        type="equity_analysis",
        status=TaskStatus.PENDING,
        resource_url="mcp://task/test_task_001",
        estimated_completion=None,
        progress=0.0,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        result=None,
        error=None,
    )


class TestTaskRegistryIntegration:
    """Integration tests using real Redis"""

    def test_register_and_get_task(self, task_registry, sample_task):
        """Test basic register and retrieve"""
        # Register task
        task_registry.register(sample_task, ttl=60)

        # Retrieve task
        retrieved = task_registry.get(sample_task.id)
        assert retrieved is not None
        assert retrieved.id == sample_task.id
        assert retrieved.type == sample_task.type
        assert retrieved.status == TaskStatus.PENDING

    def test_update_task(self, task_registry, sample_task):
        """Test updating task status"""
        # Register initial task
        task_registry.register(sample_task, ttl=60)

        # Update status
        sample_task.status = TaskStatus.RUNNING
        sample_task.progress = 0.5
        task_registry.update(sample_task)

        # Verify update
        retrieved = task_registry.get(sample_task.id)
        assert retrieved.status == TaskStatus.RUNNING
        assert retrieved.progress == 0.5

    def test_delete_task(self, task_registry, sample_task):
        """Test deleting a task"""
        # Register task
        task_registry.register(sample_task, ttl=60)

        # Verify it exists
        assert task_registry.get(sample_task.id) is not None

        # Delete
        result = task_registry.delete(sample_task.id)
        assert result is True

        # Verify it's gone
        assert task_registry.get(sample_task.id) is None

    def test_get_all_active_tasks(self, task_registry):
        """Test retrieving all active tasks"""
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task = TaskInfo(
                id=f"test_task_{i:03d}",
                type="equity_analysis",
                status=TaskStatus.PENDING,
                resource_url=f"mcp://task/test_task_{i:03d}",
                estimated_completion=None,
                progress=0.0,
                created_at=datetime.now(timezone.utc),
                updated_at=None,
                result=None,
                error=None,
            )
            tasks.append(task)
            task_registry.register(task, ttl=60)

        # Get all active tasks
        active = task_registry.get_all_active()
        assert len(active) >= 3  # At least our 3 tasks

        # Verify our tasks are in there
        task_ids = [t.id for t in active]
        for task in tasks:
            assert task.id in task_ids

    def test_get_stats(self, task_registry):
        """Test statistics aggregation"""
        # Create tasks with different statuses
        pending_task = TaskInfo(
            id="test_pending",
            type="equity_analysis",
            status=TaskStatus.PENDING,
            resource_url="mcp://task/test_pending",
            estimated_completion=None,
            progress=0.0,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            result=None,
            error=None,
        )

        running_task = TaskInfo(
            id="test_running",
            type="crypto_analysis",
            status=TaskStatus.RUNNING,
            resource_url="mcp://task/test_running",
            estimated_completion=None,
            progress=0.5,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            result=None,
            error=None,
        )

        completed_task = TaskInfo(
            id="test_completed",
            type="equity_analysis",
            status=TaskStatus.COMPLETED,
            resource_url="mcp://task/test_completed",
            estimated_completion=None,
            progress=1.0,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            result={"price": 150.0},
            error=None,
        )

        task_registry.register(pending_task, ttl=60)
        task_registry.register(running_task, ttl=60)
        task_registry.register(completed_task, ttl=60)

        # Get stats
        stats = task_registry.get_stats()

        # Verify stats structure
        assert "by_type" in stats
        assert "by_status" in stats
        assert "total_tasks" in stats

        # Should have at least 3 tasks (might have more from other tests)
        assert stats["total_tasks"] >= 3

        # Check our specific tasks are counted
        assert stats["by_status"].get(TaskStatus.PENDING.value, 0) >= 1
        assert stats["by_status"].get(TaskStatus.RUNNING.value, 0) >= 1
        assert stats["by_status"].get(TaskStatus.COMPLETED.value, 0) >= 1

        assert stats["by_type"].get("equity_analysis", 0) >= 2
        assert stats["by_type"].get("crypto_analysis", 0) >= 1

    def test_ttl_preservation_on_update(self, task_registry, sample_task, redis_client):
        """Test that update preserves remaining TTL"""
        # Register with 60 second TTL
        task_registry.register(sample_task, ttl=60)

        # Wait a moment
        import time

        time.sleep(1)

        # Update the task
        sample_task.status = TaskStatus.RUNNING
        task_registry.update(sample_task)

        # Check TTL is still reasonable (should be ~59 seconds)
        ttl = redis_client.ttl(f"fiml:task:{sample_task.id}")
        assert 55 < ttl <= 60  # Should be between 55-60 seconds

    def test_task_serialization_with_datetimes(self, task_registry):
        """Test that datetime fields serialize correctly"""
        task = TaskInfo(
            id="test_datetime",
            type="equity_analysis",
            status=TaskStatus.COMPLETED,
            resource_url="mcp://task/test_datetime",
            estimated_completion=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            progress=1.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            result={"price": 200.0},
            error=None,
        )

        task_registry.register(task, ttl=60)

        retrieved = task_registry.get(task.id)
        assert retrieved is not None
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
        assert retrieved.estimated_completion is not None

        # Datetimes should be close (within 1 second)
        assert abs((retrieved.created_at - task.created_at).total_seconds()) < 1
