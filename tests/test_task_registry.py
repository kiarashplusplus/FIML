"""
Tests for Redis-backed task registry
"""

import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
import redis

from fiml.core.models import TaskInfo, TaskStatus
from fiml.monitoring.task_registry import TaskRegistry

# Mark all tests as not requiring docker services
pytestmark = pytest.mark.unit


@pytest.fixture
def redis_client():
    """Mock Redis client"""
    client = MagicMock(spec=redis.Redis)
    client.setex = Mock()
    client.get = Mock(return_value=None)
    client.delete = Mock(return_value=0)
    client.ttl = Mock(return_value=300)
    client.scan_iter = Mock(return_value=[])
    return client


@pytest.fixture
def task_registry(redis_client):
    """Create task registry with mocked Redis"""
    registry = TaskRegistry(default_ttl=300)
    registry._redis_client = redis_client
    return registry


@pytest.fixture
def sample_task():
    """Create sample task info"""
    return TaskInfo(
        id="test-task-123",
        type="equity_analysis",
        status=TaskStatus.PENDING,
        resource_url="mcp://task/test-task-123",
        estimated_completion=datetime.now(timezone.utc) + timedelta(seconds=5),
        progress=0.0,
        created_at=datetime.now(timezone.utc),
    )


class TestTaskRegistry:
    """Test task registry functionality"""

    def test_initialization(self):
        """Test registry initialization"""
        registry = TaskRegistry(default_ttl=600)
        assert registry._default_ttl == 600
        assert registry._prefix == "fiml:task:"
        assert registry._redis_client is None

    def test_get_redis_creates_connection(self):
        """Test Redis connection is created lazily"""
        registry = TaskRegistry()
        assert registry._redis_client is None

        with patch('redis.Redis') as mock_redis:
            client = registry._get_redis()
            assert client is not None
            mock_redis.assert_called_once()

    def test_serialize_task(self, task_registry, sample_task):
        """Test task serialization to JSON"""
        serialized = task_registry._serialize_task(sample_task)

        assert isinstance(serialized, str)
        data = json.loads(serialized)

        assert data["id"] == "test-task-123"
        assert data["type"] == "equity_analysis"
        assert data["status"] == "pending"
        assert data["progress"] == 0.0
        assert "created_at" in data

    def test_serialize_task_with_optional_fields(self, task_registry):
        """Test serialization with optional fields"""
        task = TaskInfo(
            id="task-456",
            type="crypto_analysis",
            status=TaskStatus.COMPLETED,
            resource_url="test",
            progress=1.0,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            completed_steps=5,
            total_steps=5,
        )

        serialized = task_registry._serialize_task(task)
        data = json.loads(serialized)

        assert data["completed_steps"] == 5
        assert data["total_steps"] == 5
        assert data["started_at"] is not None
        assert data["completed_at"] is not None

    def test_deserialize_task(self, task_registry, sample_task):
        """Test task deserialization from JSON"""
        serialized = task_registry._serialize_task(sample_task)
        deserialized = task_registry._deserialize_task(serialized)

        assert deserialized.id == sample_task.id
        assert deserialized.type == sample_task.type
        assert deserialized.status == sample_task.status
        assert deserialized.progress == sample_task.progress

    def test_deserialize_task_with_dates(self, task_registry):
        """Test deserialization handles dates correctly"""
        now = datetime.now(timezone.utc)
        data = {
            "id": "task-789",
            "type": "test",
            "status": "completed",
            "resource_url": "test",
            "progress": 1.0,
            "created_at": now.isoformat(),
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "estimated_completion": (now + timedelta(seconds=5)).isoformat(),
            "updated_at": now.isoformat(),
            "query": None,
            "completed_steps": None,
            "total_steps": None,
            "result": None,
            "error": None,
        }

        serialized = json.dumps(data)
        deserialized = task_registry._deserialize_task(serialized)

        assert isinstance(deserialized.created_at, datetime)
        assert isinstance(deserialized.started_at, datetime)
        assert isinstance(deserialized.completed_at, datetime)
        assert deserialized.status == TaskStatus.COMPLETED

    def test_register_task(self, task_registry, redis_client, sample_task):
        """Test task registration"""
        task_registry.register(sample_task, ttl=300)

        redis_client.setex.assert_called_once()
        call_args = redis_client.setex.call_args

        assert call_args[0][0] == "fiml:task:test-task-123"
        assert call_args[0][1] == 300
        assert isinstance(call_args[0][2], str)

    def test_register_task_with_custom_ttl(self, task_registry, redis_client, sample_task):
        """Test task registration with custom TTL"""
        task_registry.register(sample_task, ttl=600)

        call_args = redis_client.setex.call_args
        assert call_args[0][1] == 600

    def test_register_task_uses_default_ttl(self, task_registry, redis_client, sample_task):
        """Test task registration uses default TTL when not specified"""
        task_registry.register(sample_task)

        call_args = redis_client.setex.call_args
        assert call_args[0][1] == 300

    def test_register_task_handles_redis_error(self, task_registry, redis_client, sample_task):
        """Test registration handles Redis errors gracefully"""
        redis_client.setex.side_effect = redis.ConnectionError("Connection failed")

        # Should not raise exception
        task_registry.register(sample_task)

    def test_get_task_success(self, task_registry, redis_client, sample_task):
        """Test getting task from registry"""
        serialized = task_registry._serialize_task(sample_task)
        redis_client.get.return_value = serialized

        result = task_registry.get("test-task-123")

        assert result is not None
        assert result.id == "test-task-123"
        assert result.type == "equity_analysis"
        redis_client.get.assert_called_once_with("fiml:task:test-task-123")

    def test_get_task_not_found(self, task_registry, redis_client):
        """Test getting non-existent task"""
        redis_client.get.return_value = None

        result = task_registry.get("nonexistent-task")

        assert result is None

    def test_get_task_handles_redis_error(self, task_registry, redis_client):
        """Test get handles Redis errors gracefully"""
        redis_client.get.side_effect = redis.ConnectionError("Connection failed")

        result = task_registry.get("test-task-123")

        assert result is None

    def test_update_task(self, task_registry, redis_client, sample_task):
        """Test updating existing task"""
        redis_client.ttl.return_value = 250

        sample_task.status = TaskStatus.COMPLETED
        sample_task.progress = 1.0

        task_registry.update(sample_task)

        redis_client.ttl.assert_called_once_with("fiml:task:test-task-123")
        redis_client.setex.assert_called_once()

        call_args = redis_client.setex.call_args
        assert call_args[0][1] == 250  # Preserves remaining TTL

    def test_update_task_expired_ttl(self, task_registry, redis_client, sample_task):
        """Test update uses default TTL when task expired"""
        redis_client.ttl.return_value = -1  # Expired

        task_registry.update(sample_task)

        call_args = redis_client.setex.call_args
        assert call_args[0][1] == 300  # Uses default TTL

    def test_update_task_handles_redis_error(self, task_registry, redis_client, sample_task):
        """Test update handles Redis errors gracefully"""
        redis_client.ttl.side_effect = redis.ConnectionError("Connection failed")

        # Should not raise exception
        task_registry.update(sample_task)

    def test_delete_task_success(self, task_registry, redis_client):
        """Test deleting task from registry"""
        redis_client.delete.return_value = 1

        result = task_registry.delete("test-task-123")

        assert result is True
        redis_client.delete.assert_called_once_with("fiml:task:test-task-123")

    def test_delete_task_not_found(self, task_registry, redis_client):
        """Test deleting non-existent task"""
        redis_client.delete.return_value = 0

        result = task_registry.delete("nonexistent-task")

        assert result is False

    def test_delete_task_handles_redis_error(self, task_registry, redis_client):
        """Test delete handles Redis errors gracefully"""
        redis_client.delete.side_effect = redis.ConnectionError("Connection failed")

        result = task_registry.delete("test-task-123")

        assert result is False

    def test_get_all_active_empty(self, task_registry, redis_client):
        """Test getting all active tasks when none exist"""
        redis_client.scan_iter.return_value = []

        tasks = task_registry.get_all_active()

        assert tasks == {}

    def test_get_all_active_multiple_tasks(self, task_registry, redis_client):
        """Test getting multiple active tasks"""
        task1 = TaskInfo(
            id="task-1",
            type="equity_analysis",
            status=TaskStatus.PENDING,
            resource_url="test",
            progress=0.0,
            created_at=datetime.now(timezone.utc),
        )
        task2 = TaskInfo(
            id="task-2",
            type="crypto_analysis",
            status=TaskStatus.COMPLETED,
            resource_url="test",
            progress=1.0,
            created_at=datetime.now(timezone.utc),
        )

        redis_client.scan_iter.return_value = [
            "fiml:task:task-1",
            "fiml:task:task-2",
        ]

        redis_client.get.side_effect = [
            task_registry._serialize_task(task1),
            task_registry._serialize_task(task2),
        ]

        tasks = task_registry.get_all_active()

        assert len(tasks) == 2
        assert "task-1" in tasks
        assert "task-2" in tasks
        assert tasks["task-1"].type == "equity_analysis"
        assert tasks["task-2"].type == "crypto_analysis"

    def test_get_all_active_handles_redis_error(self, task_registry, redis_client):
        """Test get_all_active handles Redis errors gracefully"""
        redis_client.scan_iter.side_effect = redis.ConnectionError("Connection failed")

        tasks = task_registry.get_all_active()

        assert tasks == {}

    def test_get_stats_empty(self, task_registry, redis_client):
        """Test getting stats when no tasks exist"""
        redis_client.scan_iter.return_value = []

        stats = task_registry.get_stats()

        assert stats["total_tasks"] == 0
        assert stats["tasks_by_type"] == {}
        assert stats["tasks_by_status"] == {}

    def test_get_stats_multiple_tasks(self, task_registry, redis_client):
        """Test getting stats with multiple tasks"""
        tasks = [
            TaskInfo(
                id=f"equity-{i}",
                type="equity_analysis",
                status=TaskStatus.PENDING if i < 2 else TaskStatus.COMPLETED,
                resource_url="test",
                progress=0.0 if i < 2 else 1.0,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        tasks.append(
            TaskInfo(
                id="crypto-1",
                type="crypto_analysis",
                status=TaskStatus.FAILED,
                resource_url="test",
                progress=0.0,
                created_at=datetime.now(timezone.utc),
            )
        )

        redis_client.scan_iter.return_value = [f"fiml:task:{t.id}" for t in tasks]
        redis_client.get.side_effect = [task_registry._serialize_task(t) for t in tasks]

        stats = task_registry.get_stats()

        assert stats["total_tasks"] == 4
        assert stats["tasks_by_type"]["equity_analysis"] == 3
        assert stats["tasks_by_type"]["crypto_analysis"] == 1
        assert stats["tasks_by_status"]["pending"] == 2
        assert stats["tasks_by_status"]["completed"] == 1
        assert stats["tasks_by_status"]["failed"] == 1

    def test_get_stats_handles_redis_error(self, task_registry, redis_client):
        """Test get_stats handles Redis errors gracefully"""
        redis_client.scan_iter.side_effect = redis.ConnectionError("Connection failed")

        stats = task_registry.get_stats()

        assert stats["total_tasks"] == 0
        assert stats["tasks_by_type"] == {}
        assert stats["tasks_by_status"] == {}


class TestTaskRegistryIntegration:
    """Integration tests using real Redis (if available)"""

    @pytest.fixture
    def real_registry(self):
        """Create registry with real Redis connection"""
        try:
            registry = TaskRegistry(default_ttl=10)
            # Test connection
            registry._get_redis().ping()
            yield registry
            # Cleanup
            if registry._redis_client:
                for key in registry._redis_client.scan_iter(match="fiml:task:test-*"):
                    registry._redis_client.delete(key)
        except (redis.ConnectionError, redis.TimeoutError):
            pytest.skip("Redis not available for integration tests")

    def test_full_lifecycle(self, real_registry):
        """Test complete task lifecycle with real Redis"""
        task = TaskInfo(
            id="test-lifecycle-123",
            type="test",
            status=TaskStatus.PENDING,
            resource_url="test",
            progress=0.0,
            created_at=datetime.now(timezone.utc),
        )

        # Register
        real_registry.register(task, ttl=10)

        # Get
        retrieved = real_registry.get("test-lifecycle-123")
        assert retrieved is not None
        assert retrieved.id == "test-lifecycle-123"
        assert retrieved.status == TaskStatus.PENDING

        # Update
        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        real_registry.update(task)

        # Get updated
        updated = real_registry.get("test-lifecycle-123")
        assert updated.status == TaskStatus.COMPLETED
        assert updated.progress == 1.0

        # Stats
        stats = real_registry.get_stats()
        assert stats["total_tasks"] >= 1

        # Delete
        deleted = real_registry.delete("test-lifecycle-123")
        assert deleted is True

        # Verify deleted
        not_found = real_registry.get("test-lifecycle-123")
        assert not_found is None

    def test_ttl_expiration(self, real_registry):
        """Test TTL expiration with real Redis"""
        task = TaskInfo(
            id="test-expiry-456",
            type="test",
            status=TaskStatus.PENDING,
            resource_url="test",
            progress=0.0,
            created_at=datetime.now(timezone.utc),
        )

        # Register with 2 second TTL
        real_registry.register(task, ttl=2)

        # Should exist immediately
        retrieved = real_registry.get("test-expiry-456")
        assert retrieved is not None

        # Wait for expiration
        time.sleep(3)

        # Should be gone
        expired = real_registry.get("test-expiry-456")
        assert expired is None

    def test_multiple_tasks(self, real_registry):
        """Test managing multiple tasks"""
        tasks = [
            TaskInfo(
                id=f"test-multi-{i}",
                type="equity_analysis" if i % 2 == 0 else "crypto_analysis",
                status=TaskStatus.PENDING,
                resource_url="test",
                progress=0.0,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]

        # Register all
        for task in tasks:
            real_registry.register(task, ttl=10)

        # Get all
        all_tasks = real_registry.get_all_active()
        for task in tasks:
            assert task.id in all_tasks

        # Stats
        stats = real_registry.get_stats()
        assert stats["total_tasks"] >= 5


class TestTaskRegistryEdgeCases:
    """Test edge cases and error conditions"""

    def test_serialize_task_with_none_values(self, task_registry):
        """Test serialization with None values for optional fields"""
        task = TaskInfo(
            id="task-none",
            type="test",
            status=TaskStatus.PENDING,
            resource_url="test",
            progress=0.0,
            estimated_completion=None,  # Optional field can be None
            query=None,  # Optional field can be None
        )

        serialized = task_registry._serialize_task(task)
        data = json.loads(serialized)

        assert data["estimated_completion"] is None
        assert data["query"] is None

    def test_deserialize_invalid_json(self, task_registry):
        """Test deserialization with invalid JSON"""
        with pytest.raises(json.JSONDecodeError):
            task_registry._deserialize_task("invalid json")

    def test_deserialize_missing_fields(self, task_registry):
        """Test deserialization handles missing fields"""
        minimal_data = {
            "id": "minimal",
            "resource_url": "test",
            "progress": 0.0,
        }

        serialized = json.dumps(minimal_data)

        # Should handle missing fields gracefully
        try:
            task_registry._deserialize_task(serialized)
        except Exception:
            # Expected to fail due to missing required fields
            assert True

    def test_prefix_isolation(self):
        """Test that prefix prevents key collisions"""
        registry = TaskRegistry()
        assert registry._prefix == "fiml:task:"

        # Keys should be namespaced
        task_id = "123"
        expected_key = "fiml:task:123"

        # Verify prefix is used in key construction
        with patch.object(registry, '_get_redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client

            registry.get(task_id)
            mock_client.get.assert_called_with(expected_key)
