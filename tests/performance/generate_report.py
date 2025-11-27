"""
Performance Report Generator

Generates comprehensive performance reports with:
- Summary dashboard
- Comparison to BLUEPRINT targets
- Bottleneck analysis
- Optimization recommendations
- Before/after metrics

Usage:
    python tests/performance/generate_report.py --output performance_report.md
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, List

from fiml.monitoring.performance import performance_monitor


class PerformanceReportGenerator:
    """Generate comprehensive performance reports"""

    # BLUEPRINT targets from Section 18
    TARGETS = {
        "response_time_avg": 200,  # ms
        "response_time_p99": 500,  # ms
        "cache_hit_rate": 0.80,  # 80%
        "task_completion_rate": 0.95,  # 95%
        "uptime": 0.995,  # 99.5%
        "provider_uptime": 0.99,  # 99%
    }

    def __init__(self):
        self.report_lines: List[str] = []

    def add_section(self, title: str, level: int = 2):
        """Add section header"""
        self.report_lines.append("")
        self.report_lines.append(f"{'#' * level} {title}")
        self.report_lines.append("")

    def add_text(self, text: str):
        """Add text"""
        self.report_lines.append(text)

    def add_table(self, headers: List[str], rows: List[List[str]]):
        """Add markdown table"""
        # Header
        self.report_lines.append("| " + " | ".join(headers) + " |")
        self.report_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Rows
        for row in rows:
            self.report_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        self.report_lines.append("")

    def generate_summary(self):
        """Generate executive summary"""
        self.add_section("Performance Report", level=1)
        self.add_text(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.add_text("")

        self.add_section("Executive Summary")

        metrics = performance_monitor.get_metrics_summary()
        cache_metrics = metrics.get("cache", {})
        task_metrics = metrics.get("tasks", {})

        # Overall status
        l1_hit_rate = cache_metrics.get("L1", {}).get("hit_rate", 0)
        l2_hit_rate = cache_metrics.get("L2", {}).get("hit_rate", 0)
        completion_rate = task_metrics.get("completion_rate", 0)

        overall_status = (
            "✅ PASS"
            if (
                l1_hit_rate >= self.TARGETS["cache_hit_rate"]
                and completion_rate >= self.TARGETS["task_completion_rate"]
            )
            else "⚠️ NEEDS IMPROVEMENT"
        )

        self.add_text(f"**Overall Status:** {overall_status}")
        self.add_text("")

        # Key metrics
        self.add_text("**Key Metrics:**")
        self.add_text(
            f"- L1 Cache Hit Rate: {l1_hit_rate:.2%} (Target: {self.TARGETS['cache_hit_rate']:.0%})"
        )
        self.add_text(f"- L2 Cache Hit Rate: {l2_hit_rate:.2%}")
        self.add_text(
            f"- Task Completion Rate: {completion_rate:.2%} (Target: {self.TARGETS['task_completion_rate']:.0%})"
        )
        self.add_text(f"- Slow Queries: {metrics.get('slow_queries', 0)}")
        self.add_text("")

    def generate_targets_comparison(self):
        """Compare actual metrics vs BLUEPRINT targets"""
        self.add_section("BLUEPRINT Targets Comparison")

        metrics = performance_monitor.get_metrics_summary()
        cache_metrics = metrics.get("cache", {})

        rows = []

        # Cache hit rate
        l1_hit_rate = cache_metrics.get("L1", {}).get("hit_rate", 0)
        target = self.TARGETS["cache_hit_rate"]
        status = "✅" if l1_hit_rate >= target else "❌"
        rows.append(["Cache Hit Rate", f"{target:.0%}", f"{l1_hit_rate:.2%}", status])

        # Task completion rate
        completion_rate = metrics.get("tasks", {}).get("completion_rate", 0)
        target = self.TARGETS["task_completion_rate"]
        status = "✅" if completion_rate >= target else "❌"
        rows.append(["Task Completion Rate", f"{target:.0%}", f"{completion_rate:.2%}", status])

        # Add example metrics for other targets
        rows.append(["P95 Latency", f"< {self.TARGETS['response_time_avg']}ms", "N/A", "⚠️"])

        rows.append(["P99 Latency", f"< {self.TARGETS['response_time_p99']}ms", "N/A", "⚠️"])

        rows.append(["System Uptime", f"> {self.TARGETS['uptime']:.1%}", "N/A", "⚠️"])

        self.add_table(["Metric", "Target", "Actual", "Status"], rows)

    def generate_cache_analysis(self):
        """Analyze cache performance"""
        self.add_section("Cache Performance Analysis")

        metrics = performance_monitor.get_metrics_summary()
        cache_metrics = metrics.get("cache", {})

        for layer in ["L1", "L2"]:
            layer_metrics = cache_metrics.get(layer, {})

            self.add_section(f"{layer} Cache", level=3)

            hits = layer_metrics.get("hits", 0)
            misses = layer_metrics.get("misses", 0)
            total = layer_metrics.get("total", 0)
            hit_rate = layer_metrics.get("hit_rate", 0)

            self.add_text(f"- **Total Operations:** {total}")
            self.add_text(f"- **Hits:** {hits}")
            self.add_text(f"- **Misses:** {misses}")
            self.add_text(f"- **Hit Rate:** {hit_rate:.2%}")
            self.add_text("")

            if hit_rate < self.TARGETS["cache_hit_rate"]:
                self.add_text(
                    f"⚠️ **Warning:** Hit rate below target ({self.TARGETS['cache_hit_rate']:.0%})"
                )
                self.add_text("")

    def generate_slow_queries_analysis(self):
        """Analyze slow queries"""
        self.add_section("Slow Query Analysis")

        slow_queries = performance_monitor.get_slow_queries(limit=20)

        if not slow_queries:
            self.add_text("✅ No slow queries detected.")
            return

        self.add_text(f"**Total Slow Queries:** {len(slow_queries)}")
        self.add_text("")

        # Group by operation
        by_operation: Dict[str, List] = {}
        for query in slow_queries:
            op = query["operation"]
            if op not in by_operation:
                by_operation[op] = []
            by_operation[op].append(query)

        self.add_text("**By Operation:**")
        for op, queries in sorted(by_operation.items(), key=lambda x: len(x[1]), reverse=True):
            avg_duration = sum(q["duration_seconds"] for q in queries) / len(queries)
            self.add_text(f"- `{op}`: {len(queries)} queries, avg {avg_duration:.2f}s")

        self.add_text("")

        # Top 10 slowest
        self.add_section("Top 10 Slowest Queries", level=3)

        sorted_queries = sorted(slow_queries, key=lambda x: x["duration_seconds"], reverse=True)[
            :10
        ]

        rows = []
        for q in sorted_queries:
            rows.append([q["operation"], f"{q['duration_seconds']:.2f}s", q["timestamp"]])

        self.add_table(["Operation", "Duration", "Timestamp"], rows)

    def generate_bottleneck_analysis(self):
        """Analyze performance bottlenecks"""
        self.add_section("Bottleneck Analysis")

        self.add_text("**Common Bottlenecks Identified:**")
        self.add_text("")

        # Check slow queries
        slow_queries = performance_monitor.get_slow_queries()
        if slow_queries:
            self.add_text(f"1. **Slow Queries:** {len(slow_queries)} queries >1s detected")
            self.add_text("   - Review query patterns")
            self.add_text("   - Add database indexes")
            self.add_text("   - Optimize N+1 query patterns")
            self.add_text("")

        # Check cache hit rate
        metrics = performance_monitor.get_metrics_summary()
        cache_metrics = metrics.get("cache", {})
        l1_hit_rate = cache_metrics.get("L1", {}).get("hit_rate", 0)

        if l1_hit_rate < self.TARGETS["cache_hit_rate"]:
            self.add_text(
                f"2. **Low Cache Hit Rate:** {l1_hit_rate:.2%} < {self.TARGETS['cache_hit_rate']:.0%}"
            )
            self.add_text("   - Review cache key strategy")
            self.add_text("   - Increase cache TTL for stable data")
            self.add_text("   - Implement cache warming")
            self.add_text("")

        # Provider latency
        self.add_text("3. **Provider API Latency:**")
        self.add_text("   - Monitor provider response times")
        self.add_text("   - Implement request batching")
        self.add_text("   - Add circuit breakers")
        self.add_text("")

    def generate_recommendations(self):
        """Generate optimization recommendations"""
        self.add_section("Optimization Recommendations")

        metrics = performance_monitor.get_metrics_summary()
        cache_metrics = metrics.get("cache", {})
        l1_hit_rate = cache_metrics.get("L1", {}).get("hit_rate", 0)

        self.add_section("High Priority", level=3)

        if l1_hit_rate < self.TARGETS["cache_hit_rate"]:
            self.add_text("1. **Improve Cache Hit Rate**")
            self.add_text("   - Current: {:.2%}".format(l1_hit_rate))
            self.add_text("   - Target: {:.0%}".format(self.TARGETS["cache_hit_rate"]))
            self.add_text("   - Actions:")
            self.add_text("     - Implement cache warming on startup")
            self.add_text("     - Increase TTL for rarely-changing data")
            self.add_text("     - Add predictive cache population")
            self.add_text("")

        slow_queries = performance_monitor.get_slow_queries()
        if slow_queries:
            self.add_text("2. **Optimize Slow Queries**")
            self.add_text(f"   - Count: {len(slow_queries)}")
            self.add_text("   - Actions:")
            self.add_text("     - Add database indexes")
            self.add_text("     - Use query result caching")
            self.add_text("     - Implement pagination")
            self.add_text("")

        self.add_section("Medium Priority", level=3)

        self.add_text("1. **Database Optimization**")
        self.add_text("   - Add indexes on frequently queried columns")
        self.add_text("   - Tune PostgreSQL configuration")
        self.add_text("   - Optimize connection pool size")
        self.add_text("")

        self.add_text("2. **Provider API Optimization**")
        self.add_text("   - Implement request batching")
        self.add_text("   - Add response caching")
        self.add_text("   - Use connection pooling")
        self.add_text("")

        self.add_section("Low Priority", level=3)

        self.add_text("1. **Serialization Optimization**")
        self.add_text("   - Profile serialization overhead")
        self.add_text("   - Consider MessagePack for internal communication")
        self.add_text("   - Optimize Pydantic model validation")
        self.add_text("")

    def generate_next_steps(self):
        """Generate next steps"""
        self.add_section("Next Steps")

        self.add_text("1. **Immediate Actions:**")
        self.add_text("   - [ ] Review and address slow queries")
        self.add_text("   - [ ] Implement cache warming")
        self.add_text("   - [ ] Add missing database indexes")
        self.add_text("")

        self.add_text("2. **Short Term (1-2 weeks):**")
        self.add_text("   - [ ] Run load tests under production conditions")
        self.add_text("   - [ ] Implement recommended optimizations")
        self.add_text("   - [ ] Set up continuous performance monitoring")
        self.add_text("")

        self.add_text("3. **Long Term (1-3 months):**")
        self.add_text("   - [ ] Achieve all BLUEPRINT targets")
        self.add_text("   - [ ] Implement performance regression detection in CI")
        self.add_text("   - [ ] Build performance dashboard")
        self.add_text("")

    def generate_report(self) -> str:
        """Generate complete report"""
        self.report_lines = []

        self.generate_summary()
        self.generate_targets_comparison()
        self.generate_cache_analysis()
        self.generate_slow_queries_analysis()
        self.generate_bottleneck_analysis()
        self.generate_recommendations()
        self.generate_next_steps()

        return "\n".join(self.report_lines)

    def save_report(self, filepath: str):
        """Save report to file"""
        report = self.generate_report()
        with open(filepath, "w") as f:
            f.write(report)
        print(f"Report saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Generate performance report")
    parser.add_argument(
        "--output", type=str, default="PERFORMANCE_REPORT.md", help="Output file path"
    )

    args = parser.parse_args()

    generator = PerformanceReportGenerator()
    generator.save_report(args.output)

    # Also print to console
    print("\n" + generator.generate_report())

    return 0


if __name__ == "__main__":
    sys.exit(main())
