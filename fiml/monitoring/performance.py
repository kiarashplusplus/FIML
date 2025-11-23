"""
Performance Monitoring Module

Provides detailed timing, slow query tracking, and Prometheus metrics.

Features:
- Request timing middleware
- Slow query detection and logging
- Provider latency tracking
- Cache performance metrics
- Prometheus metrics export

Usage:
    from fiml.monitoring.performance import performance_monitor

    # Track operation
    with performance_monitor.track("operation_name"):
        # ... do work ...
        pass

    # Track async operation
    async with performance_monitor.track_async("async_operation"):
        # ... do async work ...
        pass

    # Get metrics
    metrics = performance_monitor.get_metrics()
"""

import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from prometheus_client import Counter, Gauge, Histogram

from fiml.core.logging import get_logger

logger = get_logger(__name__)


# Prometheus Metrics
REQUEST_COUNT = Counter(
    "fiml_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "fiml_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
)

PROVIDER_REQUESTS = Counter(
    "fiml_provider_requests_total",
    "Total provider API requests",
    ["provider", "operation", "status"],
)

PROVIDER_LATENCY = Histogram(
    "fiml_provider_latency_seconds",
    "Provider API latency",
    ["provider", "operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

SLOW_QUERIES = Counter(
    "fiml_slow_queries_total",
    "Total slow queries (>1s)",
    ["operation"],
)

ACTIVE_REQUESTS = Gauge(
    "fiml_active_requests",
    "Number of active requests",
)

TASK_COMPLETION_RATE = Gauge(
    "fiml_task_completion_rate",
    "Task completion rate",
)

NARRATIVE_GENERATION_TIME = Histogram(
    "fiml_narrative_generation_seconds",
    "Narrative generation time",
    ["style"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
)

DSL_EXECUTION_TIME = Histogram(
    "fiml_dsl_execution_seconds",
    "DSL query execution time",
    ["query_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)


class PerformanceMonitor:
    """
    Performance monitoring and metrics collection

    Tracks timing, slow queries, and exports metrics to Prometheus.
    """

    def __init__(self) -> None:
        self._slow_query_threshold = 1.0  # 1 second
        self._slow_queries: List[Dict] = []
        self._operation_times: Dict[str, List[float]] = {}

        # Cache metrics
        self._cache_hits = {"L1": 0, "L2": 0}
        self._cache_misses = {"L1": 0, "L2": 0}

        # Task metrics
        self._tasks_completed = 0
        self._tasks_failed = 0

    @contextmanager
    def track(self, operation: str, threshold: Optional[float] = None) -> None:
        """
        Track synchronous operation timing

        Args:
            operation: Operation name
            threshold: Custom slow query threshold (seconds)
        """
        start = time.perf_counter()

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._record_timing(operation, elapsed, threshold)

    @asynccontextmanager
    async def track_async(self, operation: str, threshold: Optional[float] = None) -> None:
        """
        Track asynchronous operation timing

        Args:
            operation: Operation name
            threshold: Custom slow query threshold (seconds)
        """
        start = time.perf_counter()

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._record_timing(operation, elapsed, threshold)

    def _record_timing(self, operation: str, elapsed: float, threshold: Optional[float] = None) -> None:
        """Record operation timing"""
        # Store timing
        if operation not in self._operation_times:
            self._operation_times[operation] = []
        self._operation_times[operation].append(elapsed)

        # Keep only last 1000 timings
        if len(self._operation_times[operation]) > 1000:
            self._operation_times[operation] = self._operation_times[operation][-1000:]

        # Check for slow query
        threshold = threshold or self._slow_query_threshold
        if elapsed > threshold:
            self._record_slow_query(operation, elapsed)

    def _record_slow_query(self, operation: str, elapsed: float) -> None:
        """Record slow query"""
        slow_query = {
            "operation": operation,
            "duration_seconds": elapsed,
            "timestamp": datetime.now().isoformat(),
        }

        self._slow_queries.append(slow_query)

        # Keep only last 100 slow queries
        if len(self._slow_queries) > 100:
            self._slow_queries = self._slow_queries[-100:]

        # Log slow query
        logger.warning(
            "Slow query detected",
            operation=operation,
            duration_seconds=elapsed,
        )

        # Update Prometheus metric
        SLOW_QUERIES.labels(operation=operation).inc()

    def record_cache_hit(self, layer: str) -> None:
        """Record cache hit (metrics tracked by cache.analytics module)"""
        self._cache_hits[layer] = self._cache_hits.get(layer, 0) + 1

    def record_cache_miss(self, layer: str) -> None:
        """Record cache miss (metrics tracked by cache.analytics module)"""
        self._cache_misses[layer] = self._cache_misses.get(layer, 0) + 1

    def record_cache_operation(self, operation: str, layer: str, elapsed: float) -> None:
        """Record cache operation timing (metrics tracked by cache.analytics module)"""
        pass

    def record_provider_request(self, provider: str, operation: str, elapsed: float, success: bool) -> None:
        """Record provider API request"""
        status = "success" if success else "error"
        PROVIDER_REQUESTS.labels(provider=provider, operation=operation, status=status).inc()
        PROVIDER_LATENCY.labels(provider=provider, operation=operation).observe(elapsed)

    def record_request(self, method: str, endpoint: str, status: int, elapsed: float) -> None:
        """Record HTTP request"""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(elapsed)

    def record_task_completion(self, success: bool) -> None:
        """Record task completion"""
        if success:
            self._tasks_completed += 1
        else:
            self._tasks_failed += 1

        total = self._tasks_completed + self._tasks_failed
        if total > 0:
            completion_rate = self._tasks_completed / total
            TASK_COMPLETION_RATE.set(completion_rate)

    def record_narrative_generation(self, style: str, elapsed: float) -> None:
        """Record narrative generation time"""
        NARRATIVE_GENERATION_TIME.labels(style=style).observe(elapsed)

    def record_dsl_execution(self, query_type: str, elapsed: float) -> None:
        """Record DSL execution time"""
        DSL_EXECUTION_TIME.labels(query_type=query_type).observe(elapsed)

    def get_slow_queries(self, limit: int = 100) -> List[Dict]:
        """Get recent slow queries"""
        return self._slow_queries[-limit:]

    def get_operation_stats(self, operation: str) -> Optional[Dict]:
        """Get statistics for an operation"""
        if operation not in self._operation_times:
            return None

        timings = self._operation_times[operation]
        sorted_timings = sorted(timings)
        n = len(sorted_timings)

        return {
            "operation": operation,
            "count": n,
            "min": min(sorted_timings),
            "max": max(sorted_timings),
            "mean": sum(sorted_timings) / n,
            "p50": sorted_timings[n // 2],
            "p95": sorted_timings[int(n * 0.95)] if n > 0 else 0,
            "p99": sorted_timings[int(n * 0.99)] if n > 0 else 0,
        }

    def get_all_operations(self) -> List[str]:
        """Get all tracked operations"""
        return list(self._operation_times.keys())

    def get_cache_metrics(self) -> Dict:
        """Get cache metrics summary"""
        metrics = {}

        for layer in ["L1", "L2"]:
            hits = self._cache_hits.get(layer, 0)
            misses = self._cache_misses.get(layer, 0)
            total = hits + misses

            metrics[layer] = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": hits / total if total > 0 else 0,
            }

        return metrics

    def get_metrics_summary(self) -> Dict:
        """Get comprehensive metrics summary"""
        return {
            "cache": self.get_cache_metrics(),
            "slow_queries": len(self._slow_queries),
            "operations": {
                op: self.get_operation_stats(op)
                for op in self.get_all_operations()
            },
            "tasks": {
                "completed": self._tasks_completed,
                "failed": self._tasks_failed,
                "completion_rate": (
                    self._tasks_completed / (self._tasks_completed + self._tasks_failed)
                    if (self._tasks_completed + self._tasks_failed) > 0
                    else 0
                ),
            },
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# FastAPI Middleware for request tracking
class PerformanceMiddleware:
    """FastAPI middleware for performance tracking"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Track active requests
        ACTIVE_REQUESTS.inc()

        start = time.perf_counter()
        method = scope["method"]
        path = scope["path"]

        # Track request
        status = 200

        async def send_wrapper(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start

            # Record metrics
            performance_monitor.record_request(method, path, status, elapsed)

            # Log slow requests
            if elapsed > 1.0:
                logger.warning(
                    "Slow request",
                    method=method,
                    path=path,
                    duration_seconds=elapsed,
                )

            ACTIVE_REQUESTS.dec()


def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics for API endpoint"""
    return performance_monitor.get_metrics_summary()


def get_slow_queries(limit: int = 100) -> List[Dict]:
    """Get slow queries for API endpoint"""
    return performance_monitor.get_slow_queries(limit)
