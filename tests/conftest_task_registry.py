"""Custom conftest for task_registry tests that uses the existing Docker Redis on port 6380"""
import pytest
import redis

from fiml.core.models import TaskInfo, TaskStatus, TaskType
from fiml.monitoring.task_registry import TaskRegistry


@pytest.fixture
def redis_client():
    """Provide a real Redis client connected to the Docker Redis on port 6380"""
    client = redis.Redis(host='localhost', port=6380, db=0, decode_responses=False)
    yield client
    # Cleanup: delete all task keys
    for key in client.scan_iter("fiml:task:*"):
        client.delete(key)
    client.close()


@pytest.fixture
def task_registry(redis_client):
    """Provide a TaskRegistry instance connected to real Redis"""
    registry = TaskRegistry()
    # Force it to use our test Redis connection
    registry._redis = redis_client
    yield registry


@pytest.fixture
def sample_task():
    """Provide a sample TaskInfo for testing"""
    return TaskInfo(
        task_id="test_task_123",
        task_type=TaskType.EQUITY_ANALYSIS,
        status=TaskStatus.PENDING,
        query="test query",
        created_at=None,
        updated_at=None
    )
