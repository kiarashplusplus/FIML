"""
Task Registry for tracking async analysis tasks

Provides Redis-backed task tracking with TTL for task status queries.
Supports multi-process/multi-worker environments.
"""

import json
from datetime import datetime
from typing import Dict, Optional

import redis

from fiml.core.config import settings
from fiml.core.logging import get_logger
from fiml.core.models import TaskInfo, TaskStatus

logger = get_logger(__name__)


class TaskRegistry:
    """
    Registry for tracking analysis tasks

    Stores task information in Redis with configurable TTL for status queries.
    Thread-safe and works across multiple processes/workers.
    """

    def __init__(self, default_ttl: int = 300):
        """
        Initialize task registry

        Args:
            default_ttl: Default time-to-live for tasks in seconds (default: 5 minutes)
        """
        self._default_ttl = default_ttl
        self._redis_client: Optional[redis.Redis] = None
        self._prefix = "fiml:task:"

    def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
            )
        return self._redis_client

    def _serialize_task(self, task_info: TaskInfo) -> str:
        """Serialize TaskInfo to JSON string"""
        data = {
            "id": task_info.id,
            "type": task_info.type,
            "status": task_info.status.value if task_info.status else "unknown",
            "resource_url": task_info.resource_url,
            "estimated_completion": task_info.estimated_completion.isoformat() if task_info.estimated_completion else None,
            "progress": task_info.progress,
            "created_at": task_info.created_at.isoformat() if task_info.created_at else None,
            "updated_at": task_info.updated_at.isoformat() if task_info.updated_at else None,
            "query": getattr(task_info, 'query', None),
            "completed_steps": task_info.completed_steps,
            "total_steps": task_info.total_steps,
            "started_at": task_info.started_at.isoformat() if task_info.started_at else None,
            "completed_at": task_info.completed_at.isoformat() if task_info.completed_at else None,
            "result": getattr(task_info, 'result', None),
            "error": getattr(task_info, 'error', None),
        }
        return json.dumps(data)

    def _deserialize_task(self, data_str: str) -> TaskInfo:
        """Deserialize JSON string to TaskInfo"""
        data = json.loads(data_str)

        # Parse dates
        for date_field in ['estimated_completion', 'created_at', 'updated_at', 'started_at', 'completed_at']:
            if data.get(date_field):
                data[date_field] = datetime.fromisoformat(data[date_field])

        # Parse status enum
        if data.get('status'):
            data['status'] = TaskStatus(data['status'])

        return TaskInfo(**data)

    def register(self, task_info: TaskInfo, ttl: Optional[int] = None) -> None:
        """
        Register a task for tracking

        Args:
            task_info: Task information to register
            ttl: Optional custom TTL in seconds
        """
        try:
            redis_client = self._get_redis()
            key = f"{self._prefix}{task_info.id}"
            value = self._serialize_task(task_info)
            ttl_seconds = ttl or self._default_ttl

            redis_client.setex(key, ttl_seconds, value)

            logger.info(
                "Task registered",
                task_id=task_info.id,
                type=task_info.type,
                ttl=ttl_seconds,
            )
        except Exception as e:
            logger.error(f"Failed to register task {task_info.id}: {e}")

    def get(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get task information by ID

        Args:
            task_id: Task ID to retrieve

        Returns:
            TaskInfo if found and not expired, None otherwise
        """
        try:
            redis_client = self._get_redis()
            key = f"{self._prefix}{task_id}"
            value = redis_client.get(key)

            if value is None:
                return None

            return self._deserialize_task(value)
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    def update(self, task_info: TaskInfo) -> None:
        """
        Update existing task information

        Args:
            task_info: Updated task information
        """
        try:
            redis_client = self._get_redis()
            key = f"{self._prefix}{task_info.id}"

            # Get remaining TTL
            ttl = redis_client.ttl(key)
            if ttl <= 0:
                ttl = self._default_ttl

            value = self._serialize_task(task_info)
            redis_client.setex(key, ttl, value)

            logger.debug(
                "Task updated",
                task_id=task_info.id,
                status=task_info.status.value if task_info.status else "unknown",
            )
        except Exception as e:
            logger.error(f"Failed to update task {task_info.id}: {e}")

    def delete(self, task_id: str) -> bool:
        """
        Remove task from registry

        Args:
            task_id: Task ID to remove

        Returns:
            True if task was found and removed, False otherwise
        """
        try:
            redis_client = self._get_redis()
            key = f"{self._prefix}{task_id}"
            result = redis_client.delete(key)

            if result > 0:
                logger.debug("Task deleted", task_id=task_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False

    def get_all_active(self) -> Dict[str, TaskInfo]:
        """
        Get all active (non-expired) tasks

        Returns:
            Dictionary of task_id -> TaskInfo for all active tasks
        """
        try:
            redis_client = self._get_redis()
            pattern = f"{self._prefix}*"
            tasks = {}

            for key in redis_client.scan_iter(match=pattern):
                value = redis_client.get(key)
                if value:
                    task_info = self._deserialize_task(value)
                    tasks[task_info.id] = task_info

            return tasks
        except Exception as e:
            logger.error(f"Failed to get all active tasks: {e}")
            return {}

    def get_stats(self) -> dict:
        """
        Get registry statistics

        Returns:
            Statistics about task registry
        """
        try:
            tasks = self.get_all_active()

            tasks_by_type: Dict[str, int] = {}
            tasks_by_status: Dict[str, int] = {}

            for task_info in tasks.values():
                # Count by type
                task_type = task_info.type or "unknown"
                tasks_by_type[task_type] = tasks_by_type.get(task_type, 0) + 1

                # Count by status
                status = task_info.status.value if task_info.status else "unknown"
                tasks_by_status[status] = tasks_by_status.get(status, 0) + 1

            return {
                "total_tasks": len(tasks),
                "tasks_by_type": tasks_by_type,
                "tasks_by_status": tasks_by_status,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_tasks": 0,
                "tasks_by_type": {},
                "tasks_by_status": {},
            }


# Global task registry instance
task_registry = TaskRegistry(default_ttl=300)  # 5 minutes default
