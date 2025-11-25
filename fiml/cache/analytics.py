"""
Cache Analytics - Comprehensive cache performance monitoring
Tracks hit/miss rates, latency, and exports metrics to Prometheus
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fiml.core.logging import get_logger
from fiml.core.models import DataType

logger = get_logger(__name__)


# Prometheus metrics (optional - will work without prometheus_client)
try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available - metrics export disabled")


class DataTypeMetrics:
    """Metrics for a specific data type"""

    def __init__(self, data_type: DataType):
        self.data_type = data_type
        self.hits = 0
        self.misses = 0
        self.latencies: List[float] = []
        self.errors = 0

    def record_hit(self, latency_ms: float) -> None:
        """Record a cache hit"""
        self.hits += 1
        self.latencies.append(latency_ms)

        # Keep only last 10000 measurements
        if len(self.latencies) > 10000:
            self.latencies.pop(0)

    def record_miss(self) -> None:
        """Record a cache miss"""
        self.misses += 1

    def record_error(self) -> None:
        """Record an error"""
        self.errors += 1

    def get_hit_rate(self) -> float:
        """Calculate hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def get_latency_stats(self) -> Dict[str, float]:
        """Calculate latency statistics"""
        if not self.latencies:
            return {
                "count": 0,
                "mean": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "min": 0.0,
                "max": 0.0,
            }

        sorted_latencies = sorted(self.latencies)
        count = len(sorted_latencies)

        return {
            "count": count,
            "mean": sum(sorted_latencies) / count,
            "p50": self._percentile(sorted_latencies, 50),
            "p95": self._percentile(sorted_latencies, 95),
            "p99": self._percentile(sorted_latencies, 99),
            "min": sorted_latencies[0],
            "max": sorted_latencies[-1],
        }

    @staticmethod
    def _percentile(sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0

        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


class CacheAnalytics:
    """
    Comprehensive cache analytics and monitoring

    Features:
    - Hit/miss rate tracking per data type
    - Latency monitoring (p50, p95, p99)
    - Cache pollution detection
    - Optimization recommendations
    - Prometheus metrics export
    """

    def __init__(self, enable_prometheus: bool = True):
        """
        Initialize cache analytics

        Args:
            enable_prometheus: Enable Prometheus metrics export
        """
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE

        # Per-data-type metrics
        self.data_type_metrics: Dict[DataType, DataTypeMetrics] = {
            data_type: DataTypeMetrics(data_type)
            for data_type in DataType
        }

        # Overall metrics
        self.total_hits = 0
        self.total_misses = 0
        self.total_errors = 0

        # Cache pollution tracking
        self.single_access_keys: Dict[str, datetime] = {}
        self.evicted_before_use: int = 0

        # Time-series data (hourly buckets)
        self.hourly_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"hits": 0, "misses": 0, "requests": 0}
        )

        # Prometheus metrics
        if self.enable_prometheus:
            self._init_prometheus_metrics()

    def _init_prometheus_metrics(self) -> None:
        """Initialize Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            return

        # Cache hits/misses
        self.prom_cache_hits = Counter(
            "fiml_cache_hits_total",
            "Total cache hits",
            ["data_type", "cache_level"]
        )

        self.prom_cache_misses = Counter(
            "fiml_cache_misses_total",
            "Total cache misses",
            ["data_type", "cache_level"]
        )

        # Cache latency
        self.prom_cache_latency = Histogram(
            "fiml_cache_latency_seconds",
            "Cache operation latency",
            ["data_type", "cache_level", "operation"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )

        # Hit rate gauge
        self.prom_hit_rate = Gauge(
            "fiml_cache_hit_rate",
            "Cache hit rate percentage",
            ["data_type"]
        )

        # Cache size
        self.prom_cache_size = Gauge(
            "fiml_cache_size_bytes",
            "Cache size in bytes",
            ["cache_level"]
        )

        # Evictions
        self.prom_evictions = Counter(
            "fiml_cache_evictions_total",
            "Total cache evictions",
            ["cache_level", "reason"]
        )

        logger.info("Prometheus metrics initialized")

    def record_cache_access(
        self,
        data_type: DataType,
        is_hit: bool,
        latency_ms: float,
        cache_level: str = "l1",
        key: Optional[str] = None
    ) -> None:
        """
        Record a cache access

        Args:
            data_type: Type of data accessed
            is_hit: Whether it was a cache hit
            latency_ms: Access latency in milliseconds
            cache_level: Cache level (l1/l2)
            key: Cache key (for pollution tracking)
        """
        # Update data type metrics
        if is_hit:
            self.data_type_metrics[data_type].record_hit(latency_ms)
            self.total_hits += 1
        else:
            self.data_type_metrics[data_type].record_miss()
            self.total_misses += 1

        # Update hourly stats
        hour_key = datetime.now(UTC).strftime("%Y-%m-%d-%H")
        self.hourly_stats[hour_key]["requests"] += 1
        if is_hit:
            self.hourly_stats[hour_key]["hits"] += 1
        else:
            self.hourly_stats[hour_key]["misses"] += 1

        # Track single-access keys for pollution detection
        if key and is_hit:
            if key in self.single_access_keys:
                # Key accessed more than once - remove from tracking
                del self.single_access_keys[key]
            else:
                # First access - track it
                self.single_access_keys[key] = datetime.now(UTC)

        # Update Prometheus metrics
        if self.enable_prometheus:
            if is_hit:
                self.prom_cache_hits.labels(
                    data_type=data_type.value,
                    cache_level=cache_level
                ).inc()
            else:
                self.prom_cache_misses.labels(
                    data_type=data_type.value,
                    cache_level=cache_level
                ).inc()

            self.prom_cache_latency.labels(
                data_type=data_type.value,
                cache_level=cache_level,
                operation="get"
            ).observe(latency_ms / 1000)  # Convert to seconds

    def record_error(self, data_type: DataType) -> None:
        """Record a cache error"""
        self.data_type_metrics[data_type].record_error()
        self.total_errors += 1

    def record_eviction(
        self,
        key: str,
        reason: str = "lru",
        cache_level: str = "l1"
    ) -> None:
        """
        Record a cache eviction

        Args:
            key: Evicted key
            reason: Eviction reason (lru/lfu/ttl)
            cache_level: Cache level
        """
        # Check if key was never accessed
        if key in self.single_access_keys:
            self.evicted_before_use += 1
            del self.single_access_keys[key]

        # Update Prometheus metrics
        if self.enable_prometheus:
            self.prom_evictions.labels(
                cache_level=cache_level,
                reason=reason
            ).inc()

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall cache statistics"""
        total_requests = self.total_hits + self.total_misses
        hit_rate = (self.total_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "total_requests": total_requests,
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "total_errors": self.total_errors,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def get_data_type_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics per data type"""
        stats = {}

        for data_type, metrics in self.data_type_metrics.items():
            latency_stats = metrics.get_latency_stats()

            stats[data_type.value] = {
                "hits": metrics.hits,
                "misses": metrics.misses,
                "errors": metrics.errors,
                "hit_rate_percent": round(metrics.get_hit_rate(), 2),
                "latency_ms": {
                    "mean": round(latency_stats["mean"], 2),
                    "p50": round(latency_stats["p50"], 2),
                    "p95": round(latency_stats["p95"], 2),
                    "p99": round(latency_stats["p99"], 2),
                    "min": round(latency_stats["min"], 2),
                    "max": round(latency_stats["max"], 2),
                }
            }

            # Update Prometheus hit rate gauge
            if self.enable_prometheus:
                self.prom_hit_rate.labels(
                    data_type=data_type.value
                ).set(metrics.get_hit_rate())

        return stats

    def detect_cache_pollution(self) -> Dict[str, Any]:
        """
        Detect cache pollution issues

        Returns:
            Dict with pollution metrics and problematic patterns
        """
        # Clean old single-access keys (>1 hour old)
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        old_keys = [
            key for key, timestamp in self.single_access_keys.items()
            if timestamp < cutoff
        ]

        pollution_score = len(old_keys) / max(len(self.single_access_keys), 1) * 100

        return {
            "single_access_keys": len(self.single_access_keys),
            "old_single_access_keys": len(old_keys),
            "evicted_before_reuse": self.evicted_before_use,
            "pollution_score_percent": round(pollution_score, 2),
            "is_polluted": pollution_score > 30,  # >30% single-access keys
        }

    def get_hourly_trends(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get hourly cache trends

        Args:
            hours: Number of hours to include

        Returns:
            List of hourly stats
        """
        now = datetime.now(UTC)
        trends = []

        for i in range(hours):
            hour_time = now - timedelta(hours=i)
            hour_key = hour_time.strftime("%Y-%m-%d-%H")

            stats = self.hourly_stats.get(hour_key, {"hits": 0, "misses": 0, "requests": 0})
            hit_rate = (stats["hits"] / stats["requests"] * 100) if stats["requests"] > 0 else 0.0

            trends.append({
                "hour": hour_time.strftime("%Y-%m-%d %H:00"),
                "requests": stats["requests"],
                "hits": stats["hits"],
                "misses": stats["misses"],
                "hit_rate_percent": round(hit_rate, 2),
            })

        return list(reversed(trends))

    def generate_recommendations(self) -> List[str]:
        """
        Generate cache optimization recommendations

        Returns:
            List of recommendation strings
        """
        recommendations = []

        overall = self.get_overall_stats()
        pollution = self.detect_cache_pollution()
        data_type_stats = self.get_data_type_stats()

        # Overall hit rate
        if overall["hit_rate_percent"] < 70:
            recommendations.append(
                f"Low overall hit rate ({overall['hit_rate_percent']:.1f}%). "
                "Consider enabling cache warming or increasing cache size."
            )

        # Cache pollution
        if pollution["is_polluted"]:
            recommendations.append(
                f"Cache pollution detected ({pollution['pollution_score_percent']:.1f}% single-access keys). "
                "Review TTL settings or implement smarter eviction policies."
            )

        # High evictions before reuse
        if pollution["evicted_before_reuse"] > 100:
            recommendations.append(
                f"High eviction before reuse count ({pollution['evicted_before_reuse']}). "
                "Cache size may be too small or TTL too short."
            )

        # Per-data-type recommendations
        for data_type, stats in data_type_stats.items():
            if stats["hit_rate_percent"] < 60:
                recommendations.append(
                    f"Low hit rate for {data_type} ({stats['hit_rate_percent']:.1f}%). "
                    f"Consider longer TTL or pre-warming."
                )

            if stats["latency_ms"]["p99"] > 100:
                recommendations.append(
                    f"High p99 latency for {data_type} ({stats['latency_ms']['p99']:.1f}ms). "
                    f"Investigate slow cache operations."
                )

        if not recommendations:
            recommendations.append("Cache performance is optimal. No recommendations at this time.")

        return recommendations

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive analytics report"""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "overall": self.get_overall_stats(),
            "by_data_type": self.get_data_type_stats(),
            "pollution": self.detect_cache_pollution(),
            "hourly_trends": self.get_hourly_trends(24),
            "recommendations": self.generate_recommendations(),
            "prometheus_enabled": self.enable_prometheus,
        }

    def reset_stats(self) -> None:
        """Reset all statistics"""
        self.total_hits = 0
        self.total_misses = 0
        self.total_errors = 0
        self.single_access_keys.clear()
        self.evicted_before_use = 0
        self.hourly_stats.clear()

        for metrics in self.data_type_metrics.values():
            metrics.hits = 0
            metrics.misses = 0
            metrics.errors = 0
            metrics.latencies.clear()

        logger.info("Cache analytics stats reset")


# Global analytics instance
cache_analytics = CacheAnalytics(enable_prometheus=True)
