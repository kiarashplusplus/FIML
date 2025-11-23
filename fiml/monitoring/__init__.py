"""Performance monitoring module"""

from fiml.monitoring.performance import (
    DSL_EXECUTION_TIME,
    NARRATIVE_GENERATION_TIME,
    PROVIDER_LATENCY,
    PROVIDER_REQUESTS,
    REQUEST_COUNT,
    REQUEST_DURATION,
    SLOW_QUERIES,
    TASK_COMPLETION_RATE,
    PerformanceMiddleware,
    PerformanceMonitor,
    get_performance_metrics,
    get_slow_queries,
    performance_monitor,
)

__all__ = [
    "performance_monitor",
    "PerformanceMonitor",
    "PerformanceMiddleware",
    "get_performance_metrics",
    "get_slow_queries",
    # Prometheus metrics
    "REQUEST_COUNT",
    "REQUEST_DURATION",
    "PROVIDER_REQUESTS",
    "PROVIDER_LATENCY",
    "SLOW_QUERIES",
    "TASK_COMPLETION_RATE",
    "NARRATIVE_GENERATION_TIME",
    "DSL_EXECUTION_TIME",
]
