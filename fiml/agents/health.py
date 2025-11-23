"""
Worker Health Monitoring and Metrics

Provides health checks, metrics collection, and monitoring for workers.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from fiml.core.logging import get_logger

logger = get_logger(__name__)


class WorkerStatus(str, Enum):
    """Worker health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    INITIALIZING = "initializing"
    SHUTDOWN = "shutdown"


@dataclass
class WorkerMetrics:
    """Metrics for a single worker"""
    worker_id: str
    worker_type: str
    
    # Task statistics
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_timeout: int = 0
    tasks_in_progress: int = 0
    
    # Performance metrics
    total_execution_time: float = 0.0  # seconds
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    
    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_pct: float = 0.0
    
    # Health status
    status: WorkerStatus = WorkerStatus.INITIALIZING
    last_heartbeat: Optional[datetime] = None
    error_messages: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_task_at: Optional[datetime] = None
    
    @property
    def avg_execution_time(self) -> float:
        """Calculate average execution time"""
        if self.tasks_completed == 0:
            return 0.0
        return self.total_execution_time / self.tasks_completed
    
    @property
    def success_rate(self) -> float:
        """Calculate task success rate"""
        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks == 0:
            return 1.0
        return self.tasks_completed / total_tasks
    
    @property
    def error_rate(self) -> float:
        """Calculate task error rate"""
        return 1.0 - self.success_rate
    
    def record_task_success(self, execution_time: float) -> None:
        """Record a successful task completion"""
        self.tasks_completed += 1
        self.total_execution_time += execution_time
        self.min_execution_time = min(self.min_execution_time, execution_time)
        self.max_execution_time = max(self.max_execution_time, execution_time)
        self.last_task_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        
    def record_task_failure(self, error_message: str) -> None:
        """Record a failed task"""
        self.tasks_failed += 1
        self.error_messages.append(f"{datetime.utcnow().isoformat()}: {error_message}")
        # Keep only last 10 errors
        if len(self.error_messages) > 10:
            self.error_messages = self.error_messages[-10:]
        self.last_heartbeat = datetime.utcnow()
        
    def record_task_timeout(self) -> None:
        """Record a task timeout"""
        self.tasks_timeout += 1
        self.tasks_failed += 1
        self.last_heartbeat = datetime.utcnow()
        
    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp"""
        self.last_heartbeat = datetime.utcnow()
        
    def update_status(self, status: WorkerStatus) -> None:
        """Update worker health status"""
        self.status = status
        self.last_heartbeat = datetime.utcnow()
        
    def is_healthy(self, max_heartbeat_age_seconds: int = 120) -> bool:
        """Check if worker is healthy based on metrics"""
        # Check heartbeat
        if self.last_heartbeat is None:
            return False
        
        heartbeat_age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        if heartbeat_age > max_heartbeat_age_seconds:
            return False
        
        # Check error rate (default threshold: 0.5 or 50%)
        if self.error_rate > 0.5:
            return False
        
        # Check status
        if self.status in [WorkerStatus.UNHEALTHY, WorkerStatus.SHUTDOWN]:
            return False
        
        return True


class WorkerHealthMonitor:
    """
    Centralized health monitoring for all workers
    
    Features:
    - Real-time metrics collection
    - Health status tracking
    - Circuit breaker logic
    - Automatic recovery detection
    """
    
    # Configuration constants - can be overridden via settings
    DEFAULT_FAILURE_THRESHOLD = 5  # Failures before opening circuit
    DEFAULT_RECOVERY_TIMEOUT = 60  # Seconds before trying recovery
    DEFAULT_MAX_HEARTBEAT_AGE = 120  # Max seconds since last heartbeat
    DEFAULT_ERROR_RATE_THRESHOLD = 0.5  # 50% error rate threshold
    
    def __init__(self):
        self._metrics: Dict[str, WorkerMetrics] = {}
        self._circuit_breakers: Dict[str, Dict] = defaultdict(lambda: {
            "failures": 0,
            "last_failure": None,
            "state": "closed",  # closed, open, half-open
        })
        
        # Configuration - try to load from settings, otherwise use defaults
        try:
            from fiml.core.config import settings
            self._failure_threshold = getattr(settings, 'worker_circuit_breaker_threshold', self.DEFAULT_FAILURE_THRESHOLD)
            self._recovery_timeout = getattr(settings, 'worker_circuit_breaker_timeout', self.DEFAULT_RECOVERY_TIMEOUT)
            self._max_heartbeat_age = getattr(settings, 'worker_max_heartbeat_age', self.DEFAULT_MAX_HEARTBEAT_AGE)
            self._error_rate_threshold = getattr(settings, 'worker_error_rate_threshold', self.DEFAULT_ERROR_RATE_THRESHOLD)
        except Exception:
            # Fallback to defaults if settings not available
            self._failure_threshold = self.DEFAULT_FAILURE_THRESHOLD
            self._recovery_timeout = self.DEFAULT_RECOVERY_TIMEOUT
            self._max_heartbeat_age = self.DEFAULT_MAX_HEARTBEAT_AGE
            self._error_rate_threshold = self.DEFAULT_ERROR_RATE_THRESHOLD
        
    def register_worker(self, worker_id: str, worker_type: str) -> WorkerMetrics:
        """Register a new worker for monitoring"""
        if worker_id in self._metrics:
            logger.warning(f"Worker {worker_id} already registered")
            return self._metrics[worker_id]
        
        metrics = WorkerMetrics(worker_id=worker_id, worker_type=worker_type)
        self._metrics[worker_id] = metrics
        
        logger.info(f"Registered worker for monitoring", worker_id=worker_id, worker_type=worker_type)
        return metrics
    
    def get_metrics(self, worker_id: str) -> Optional[WorkerMetrics]:
        """Get metrics for a specific worker"""
        return self._metrics.get(worker_id)
    
    def get_all_metrics(self) -> Dict[str, WorkerMetrics]:
        """Get metrics for all workers"""
        return self._metrics.copy()
    
    def record_task_start(self, worker_id: str) -> float:
        """Record task start and return timestamp"""
        if worker_id in self._metrics:
            self._metrics[worker_id].tasks_in_progress += 1
            self._metrics[worker_id].update_heartbeat()
        return time.time()
    
    def record_task_complete(self, worker_id: str, start_time: float, success: bool, error: Optional[str] = None) -> None:
        """Record task completion"""
        if worker_id not in self._metrics:
            logger.warning(f"Unknown worker {worker_id}")
            return
        
        metrics = self._metrics[worker_id]
        metrics.tasks_in_progress = max(0, metrics.tasks_in_progress - 1)
        
        execution_time = time.time() - start_time
        
        if success:
            metrics.record_task_success(execution_time)
            self._record_success(worker_id)
        else:
            metrics.record_task_failure(error or "Unknown error")
            self._record_failure(worker_id)
    
    def record_task_timeout(self, worker_id: str, start_time: float) -> None:
        """Record task timeout"""
        if worker_id not in self._metrics:
            return
        
        metrics = self._metrics[worker_id]
        metrics.tasks_in_progress = max(0, metrics.tasks_in_progress - 1)
        metrics.record_task_timeout()
        self._record_failure(worker_id)
    
    def _record_failure(self, worker_id: str) -> None:
        """Record failure for circuit breaker logic"""
        cb = self._circuit_breakers[worker_id]
        cb["failures"] += 1
        cb["last_failure"] = time.time()
        
        # Open circuit if threshold exceeded
        if cb["failures"] >= self._failure_threshold and cb["state"] == "closed":
            cb["state"] = "open"
            logger.warning(f"Circuit breaker opened for worker {worker_id}")
            
            if worker_id in self._metrics:
                self._metrics[worker_id].update_status(WorkerStatus.UNHEALTHY)
    
    def _record_success(self, worker_id: str) -> None:
        """Record success for circuit breaker logic"""
        cb = self._circuit_breakers[worker_id]
        
        # Reset failures on success
        if cb["state"] == "half-open":
            cb["state"] = "closed"
            cb["failures"] = 0
            logger.info(f"Circuit breaker closed for worker {worker_id}")
            
            if worker_id in self._metrics:
                self._metrics[worker_id].update_status(WorkerStatus.HEALTHY)
        elif cb["state"] == "closed":
            # Gradually reduce failure count on success
            cb["failures"] = max(0, cb["failures"] - 1)
    
    def is_circuit_open(self, worker_id: str) -> bool:
        """Check if circuit breaker is open for a worker"""
        cb = self._circuit_breakers[worker_id]
        
        if cb["state"] == "open":
            # Check if recovery timeout has passed
            if cb["last_failure"] and (time.time() - cb["last_failure"]) > self._recovery_timeout:
                cb["state"] = "half-open"
                logger.info(f"Circuit breaker half-open for worker {worker_id}")
                return False
            return True
        
        return False
    
    def get_health_summary(self) -> Dict:
        """Get overall health summary for all workers"""
        total_workers = len(self._metrics)
        healthy_workers = sum(1 for m in self._metrics.values() if m.is_healthy(self._max_heartbeat_age))
        
        total_tasks = sum(m.tasks_completed + m.tasks_failed for m in self._metrics.values())
        total_successes = sum(m.tasks_completed for m in self._metrics.values())
        
        worker_types = defaultdict(list)
        for metrics in self._metrics.values():
            worker_types[metrics.worker_type].append(metrics)
        
        type_stats = {}
        for worker_type, metrics_list in worker_types.items():
            type_stats[worker_type] = {
                "total": len(metrics_list),
                "healthy": sum(1 for m in metrics_list if m.is_healthy(self._max_heartbeat_age)),
                "tasks_completed": sum(m.tasks_completed for m in metrics_list),
                "tasks_failed": sum(m.tasks_failed for m in metrics_list),
                "avg_execution_time": sum(m.avg_execution_time for m in metrics_list) / len(metrics_list) if metrics_list else 0,
            }
        
        return {
            "total_workers": total_workers,
            "healthy_workers": healthy_workers,
            "unhealthy_workers": total_workers - healthy_workers,
            "total_tasks": total_tasks,
            "total_successes": total_successes,
            "total_failures": total_tasks - total_successes,
            "overall_success_rate": total_successes / total_tasks if total_tasks > 0 else 1.0,
            "by_type": type_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_unhealthy_workers(self) -> List[str]:
        """Get list of unhealthy worker IDs"""
        return [
            worker_id
            for worker_id, metrics in self._metrics.items()
            if not metrics.is_healthy(self._max_heartbeat_age)
        ]


# Global health monitor instance
worker_health_monitor = WorkerHealthMonitor()
