"""
Watchdog Health Monitoring and Metrics

Provides health checks, metrics collection, and monitoring for watchdogs.
"""

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Dict, List, Optional

from fiml.core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True

    # Watchdog metrics
    WATCHDOG_CHECKS = Counter(
        "fiml_watchdog_checks_total",
        "Total watchdog checks performed",
        ["watchdog_name"]
    )

    WATCHDOG_CHECK_FAILURES = Counter(
        "fiml_watchdog_check_failures_total",
        "Total watchdog check failures",
        ["watchdog_name"]
    )

    WATCHDOG_EVENTS_DETECTED = Counter(
        "fiml_watchdog_events_detected_total",
        "Total events detected by watchdogs",
        ["watchdog_name", "severity"]
    )

    WATCHDOG_CHECK_DURATION = Histogram(
        "fiml_watchdog_check_duration_seconds",
        "Watchdog check duration",
        ["watchdog_name"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    )

    WATCHDOG_TOTAL_COUNT = Gauge(
        "fiml_watchdog_total_count",
        "Total number of registered watchdogs"
    )

    WATCHDOG_HEALTHY_COUNT = Gauge(
        "fiml_watchdog_healthy_count",
        "Number of healthy watchdogs"
    )

    WATCHDOG_UNHEALTHY_COUNT = Gauge(
        "fiml_watchdog_unhealthy_count",
        "Number of unhealthy watchdogs"
    )

    WATCHDOG_SUCCESS_RATE = Gauge(
        "fiml_watchdog_success_rate",
        "Overall watchdog success rate"
    )

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available - watchdog metrics export disabled")


@dataclass
class WatchdogMetrics:
    """Metrics for a single watchdog"""
    watchdog_name: str

    # Detection statistics
    checks_performed: int = 0
    events_detected: int = 0
    checks_failed: int = 0

    # Performance metrics
    total_check_time: float = 0.0  # seconds
    min_check_time: float = float('inf')
    max_check_time: float = 0.0

    # Health status
    is_enabled: bool = True
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_check_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None
    last_error: Optional[str] = None

    # Event severity breakdown
    critical_events: int = 0
    high_events: int = 0
    medium_events: int = 0
    low_events: int = 0

    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def avg_check_time(self) -> float:
        """Calculate average check time"""
        if self.checks_performed == 0:
            return 0.0
        return self.total_check_time / self.checks_performed

    @property
    def success_rate(self) -> float:
        """Calculate check success rate"""
        total_checks = self.checks_performed + self.checks_failed
        if total_checks == 0:
            return 1.0
        return self.checks_performed / total_checks

    @property
    def detection_rate(self) -> float:
        """Calculate event detection rate"""
        if self.checks_performed == 0:
            return 0.0
        return self.events_detected / self.checks_performed

    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds"""
        return (datetime.now(UTC) - self.started_at).total_seconds()

    def record_check_success(self, check_time: float, event_detected: bool = False, severity: Optional[str] = None) -> None:
        """Record a successful check"""
        self.checks_performed += 1
        self.total_check_time += check_time
        self.min_check_time = min(self.min_check_time, check_time)
        self.max_check_time = max(self.max_check_time, check_time)
        self.last_check_at = datetime.now(UTC)
        self.consecutive_failures = 0

        if event_detected:
            self.events_detected += 1
            self.last_event_at = datetime.now(UTC)

            # Track by severity
            if severity == "critical":
                self.critical_events += 1
            elif severity == "high":
                self.high_events += 1
            elif severity == "medium":
                self.medium_events += 1
            else:
                self.low_events += 1

    def record_check_failure(self, error_message: str) -> None:
        """Record a failed check"""
        self.checks_failed += 1
        self.consecutive_failures += 1
        self.last_error = f"{datetime.now(UTC).isoformat()}: {error_message}"
        self.last_check_at = datetime.now(UTC)

        # Mark as unhealthy if too many consecutive failures (default: 3)
        if self.consecutive_failures >= 3:
            self.is_healthy = False

    def reset_health(self) -> None:
        """Reset health status"""
        self.is_healthy = True
        self.consecutive_failures = 0


class WatchdogHealthMonitor:
    """
    Centralized health monitoring for all watchdogs

    Features:
    - Real-time metrics collection
    - Health status tracking
    - Performance monitoring
    - Event statistics
    """

    # Configuration constants
    DEFAULT_CONSECUTIVE_FAILURE_THRESHOLD = 3  # Mark unhealthy after this many failures

    def __init__(self) -> None:
        self._metrics: Dict[str, WatchdogMetrics] = {}
        self._max_check_interval_multiplier = 3  # Alert if no check in 3x expected interval
        self._consecutive_failure_threshold = self.DEFAULT_CONSECUTIVE_FAILURE_THRESHOLD
        self.enable_prometheus = PROMETHEUS_AVAILABLE

    def register_watchdog(self, watchdog_name: str) -> WatchdogMetrics:
        """Register a new watchdog for monitoring"""
        if watchdog_name in self._metrics:
            logger.warning(f"Watchdog {watchdog_name} already registered")
            return self._metrics[watchdog_name]

        metrics = WatchdogMetrics(watchdog_name=watchdog_name)
        self._metrics[watchdog_name] = metrics

        logger.info("Registered watchdog for monitoring", watchdog_name=watchdog_name)
        return metrics

    def get_metrics(self, watchdog_name: str) -> Optional[WatchdogMetrics]:
        """Get metrics for a specific watchdog"""
        return self._metrics.get(watchdog_name)

    def get_all_metrics(self) -> Dict[str, WatchdogMetrics]:
        """Get metrics for all watchdogs"""
        return self._metrics.copy()

    def record_check_start(self, watchdog_name: str) -> float:
        """Record check start and return timestamp"""
        return time.time()

    def record_check_complete(
        self,
        watchdog_name: str,
        start_time: float,
        success: bool,
        event_detected: bool = False,
        severity: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record check completion"""
        if watchdog_name not in self._metrics:
            logger.warning(f"Unknown watchdog {watchdog_name}")
            return

        metrics = self._metrics[watchdog_name]
        check_time = time.time() - start_time

        if success:
            metrics.record_check_success(check_time, event_detected, severity)

            # Update Prometheus metrics
            if self.enable_prometheus:
                WATCHDOG_CHECKS.labels(watchdog_name=watchdog_name).inc()
                WATCHDOG_CHECK_DURATION.labels(watchdog_name=watchdog_name).observe(check_time)

                if event_detected and severity:
                    WATCHDOG_EVENTS_DETECTED.labels(
                        watchdog_name=watchdog_name,
                        severity=severity
                    ).inc()
        else:
            metrics.record_check_failure(error or "Unknown error")

            # Update Prometheus metrics
            if self.enable_prometheus:
                WATCHDOG_CHECK_FAILURES.labels(watchdog_name=watchdog_name).inc()

    def enable_watchdog(self, watchdog_name: str) -> None:
        """Enable a watchdog"""
        if watchdog_name in self._metrics:
            self._metrics[watchdog_name].is_enabled = True
            logger.info("Watchdog enabled", watchdog_name=watchdog_name)

    def disable_watchdog(self, watchdog_name: str) -> None:
        """Disable a watchdog"""
        if watchdog_name in self._metrics:
            self._metrics[watchdog_name].is_enabled = False
            logger.info("Watchdog disabled", watchdog_name=watchdog_name)

    def reset_watchdog_health(self, watchdog_name: str) -> None:
        """Reset health status for a watchdog"""
        if watchdog_name in self._metrics:
            self._metrics[watchdog_name].reset_health()
            logger.info("Watchdog health reset", watchdog_name=watchdog_name)

    def get_health_summary(self) -> Dict:
        """Get overall health summary for all watchdogs"""
        total_watchdogs = len(self._metrics)
        enabled_watchdogs = sum(1 for m in self._metrics.values() if m.is_enabled)
        healthy_watchdogs = sum(1 for m in self._metrics.values() if m.is_healthy and m.is_enabled)

        total_checks = sum(m.checks_performed for m in self._metrics.values())
        total_events = sum(m.events_detected for m in self._metrics.values())
        total_failures = sum(m.checks_failed for m in self._metrics.values())

        # Event breakdown by severity
        total_critical = sum(m.critical_events for m in self._metrics.values())
        total_high = sum(m.high_events for m in self._metrics.values())
        total_medium = sum(m.medium_events for m in self._metrics.values())
        total_low = sum(m.low_events for m in self._metrics.values())

        # Calculate success rate
        overall_success_rate = (total_checks / (total_checks + total_failures)) if (total_checks + total_failures) > 0 else 1.0

        # Update Prometheus gauges
        if self.enable_prometheus:
            WATCHDOG_TOTAL_COUNT.set(total_watchdogs)
            WATCHDOG_HEALTHY_COUNT.set(healthy_watchdogs)
            WATCHDOG_UNHEALTHY_COUNT.set(enabled_watchdogs - healthy_watchdogs)
            WATCHDOG_SUCCESS_RATE.set(overall_success_rate)

        return {
            "total_watchdogs": total_watchdogs,
            "enabled_watchdogs": enabled_watchdogs,
            "healthy_watchdogs": healthy_watchdogs,
            "unhealthy_watchdogs": enabled_watchdogs - healthy_watchdogs,
            "total_checks": total_checks,
            "total_events": total_events,
            "total_failures": total_failures,
            "overall_success_rate": overall_success_rate,
            "events_by_severity": {
                "critical": total_critical,
                "high": total_high,
                "medium": total_medium,
                "low": total_low,
            },
            "detection_rate": total_events / total_checks if total_checks > 0 else 0.0,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def get_unhealthy_watchdogs(self) -> List[str]:
        """Get list of unhealthy watchdog names"""
        return [
            name
            for name, metrics in self._metrics.items()
            if not metrics.is_healthy and metrics.is_enabled
        ]

    def get_stale_watchdogs(self, max_age_seconds: int = 300) -> List[str]:
        """Get list of watchdogs that haven't checked recently"""
        stale = []
        now = datetime.now(UTC)

        for name, metrics in self._metrics.items():
            if not metrics.is_enabled:
                continue

            if metrics.last_check_at is None or (now - metrics.last_check_at).total_seconds() > max_age_seconds:
                stale.append(name)

        return stale


# Global watchdog health monitor instance
watchdog_health_monitor = WatchdogHealthMonitor()
