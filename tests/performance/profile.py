"""
Performance Profiling Script

Uses cProfile and py-spy to identify performance bottlenecks.

Features:
- Profile application code
- Identify slow functions
- Generate flame graphs
- Analyze memory usage
- Export profiling results

Usage:
    # Profile with cProfile
    python tests/performance/profile.py --mode cprofile --duration 60

    # Profile with py-spy (requires py-spy installation)
    python tests/performance/profile.py --mode pyspy --duration 60

    # Profile specific module
    python tests/performance/profile.py --target fiml.cache.manager --duration 30
"""

import argparse
import cProfile
import io
import pstats
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Profiler:
    """Performance profiler for FIML application"""

    def __init__(self, output_dir: str = "profiling_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def profile_with_cprofile(
        self, target_code: str, duration: int = 60, sort_by: str = "cumulative"
    ) -> str:
        """
        Profile code with cProfile

        Args:
            target_code: Code to profile
            duration: Duration in seconds
            sort_by: Sort stats by (cumulative, time, calls)

        Returns:
            Path to output file
        """
        print(f"Profiling with cProfile for {duration} seconds...")

        profiler = cProfile.Profile()
        profiler.enable()

        # Execute target code
        try:
            exec(target_code)
        except Exception as e:
            print(f"Error during profiling: {e}")

        profiler.disable()

        # Save stats
        output_file = self.output_dir / f"cprofile_{self.timestamp}.stats"
        profiler.dump_stats(str(output_file))

        # Generate text report
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.strip_dirs()
        ps.sort_stats(sort_by)
        ps.print_stats(50)  # Top 50 functions

        report_file = self.output_dir / f"cprofile_{self.timestamp}.txt"
        with open(report_file, "w") as f:
            f.write(s.getvalue())

        print(f"Stats saved to: {output_file}")
        print(f"Report saved to: {report_file}")

        # Print summary
        print("\nTop 10 slowest functions:")
        print(s.getvalue().split("\n")[5:15])

        return str(output_file)

    def profile_with_pyspy(
        self, pid: Optional[int] = None, duration: int = 60, rate: int = 100
    ) -> str:
        """
        Profile running process with py-spy

        Args:
            pid: Process ID (if None, profiles current script)
            duration: Duration in seconds
            rate: Sampling rate (samples per second)

        Returns:
            Path to output file
        """
        print(f"Profiling with py-spy for {duration} seconds...")

        output_file = self.output_dir / f"pyspy_{self.timestamp}.svg"

        cmd = [
            "py-spy",
            "record",
            "-o",
            str(output_file),
            "--duration",
            str(duration),
            "--rate",
            str(rate),
            "--format",
            "flamegraph",
        ]

        if pid:
            cmd.extend(["--pid", str(pid)])
        else:
            cmd.extend(["--", "python", "-m", "fiml.server"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Flame graph saved to: {output_file}")
                return str(output_file)
            else:
                print(f"py-spy failed: {result.stderr}")
                return ""
        except FileNotFoundError:
            print("py-spy not found. Install with: pip install py-spy")
            return ""

    def analyze_memory(self, target_code: str, duration: int = 60) -> str:
        """
        Analyze memory usage

        Args:
            target_code: Code to analyze
            duration: Duration in seconds

        Returns:
            Path to output file
        """
        print(f"Analyzing memory usage for {duration} seconds...")

        try:
            import importlib.util

            if importlib.util.find_spec("memory_profiler") is None:
                raise ImportError("memory_profiler not installed")

            output_file = self.output_dir / f"memory_{self.timestamp}.txt"

            # This requires memory_profiler package
            # and @profile decorator on target functions

            print("Memory profiling requires @profile decorators on target functions")
            print(f"Output file: {output_file}")

            return str(output_file)

        except ImportError:
            print("memory_profiler not found. Install with: pip install memory-profiler")
            return ""

    def profile_cache_operations(self) -> str:
        """Profile cache operations"""
        print("Profiling cache operations...")

        code = """
import asyncio
from fiml.cache.manager import cache_manager

async def benchmark_cache():
    await cache_manager.initialize()

    # Test L1 cache
    for i in range(1000):
        await cache_manager.l1.set(f"key_{i}", {"value": i}, ttl_seconds=300)

    for i in range(1000):
        await cache_manager.l1.get(f"key_{i}")

    await cache_manager.shutdown()

asyncio.run(benchmark_cache())
"""

        return self.profile_with_cprofile(code, duration=30)

    def profile_provider_fetches(self) -> str:
        """Profile provider data fetches"""
        print("Profiling provider fetches...")

        code = """
import asyncio
from fiml.providers.registry import provider_registry
from fiml.core.models import Asset, AssetType, Market

async def benchmark_providers():
    await provider_registry.initialize()

    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.EQUITY,
        market=Market.US
    )

    for i in range(50):
        try:
            await provider_registry.fetch_price(asset)
        except:
            pass

    await provider_registry.shutdown()

asyncio.run(benchmark_providers())
"""

        return self.profile_with_cprofile(code, duration=30)

    def generate_summary_report(self) -> str:
        """Generate profiling summary report"""
        report = []
        report.append("=" * 80)
        report.append("PERFORMANCE PROFILING SUMMARY")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        report.append("Profiling Files:")
        for file in sorted(self.output_dir.glob("*")):
            report.append(f"  - {file.name}")
        report.append("")

        report.append("Analysis:")
        report.append("1. Review cProfile reports for slow functions")
        report.append("2. Review flame graphs (SVG files) for bottlenecks")
        report.append("3. Check memory profiling results")
        report.append("")

        report.append("Common Bottlenecks to Look For:")
        report.append("  - Slow database queries")
        report.append("  - N+1 query patterns")
        report.append("  - Excessive API calls to providers")
        report.append("  - Inefficient serialization/deserialization")
        report.append("  - Cache key generation overhead")
        report.append("")

        report.append("=" * 80)

        report_text = "\n".join(report)

        report_file = self.output_dir / f"summary_{self.timestamp}.txt"
        with open(report_file, "w") as f:
            f.write(report_text)

        print(report_text)
        return str(report_file)


def main():
    parser = argparse.ArgumentParser(description="Performance profiling")
    parser.add_argument(
        "--mode",
        choices=["cprofile", "pyspy", "memory", "all"],
        default="cprofile",
        help="Profiling mode",
    )
    parser.add_argument(
        "--target",
        choices=["cache", "providers", "custom"],
        default="cache",
        help="What to profile",
    )
    parser.add_argument("--duration", type=int, default=60, help="Profiling duration in seconds")
    parser.add_argument("--pid", type=int, help="Process ID to profile (for py-spy)")
    parser.add_argument("--code", type=str, help="Custom code to profile")

    args = parser.parse_args()

    profiler = Profiler()

    if args.mode == "cprofile" or args.mode == "all":
        if args.target == "cache":
            profiler.profile_cache_operations()
        elif args.target == "providers":
            profiler.profile_provider_fetches()
        elif args.code:
            profiler.profile_with_cprofile(args.code, args.duration)

    if args.mode == "pyspy" or args.mode == "all":
        profiler.profile_with_pyspy(args.pid, args.duration)

    if args.mode == "memory" or args.mode == "all":
        if args.code:
            profiler.analyze_memory(args.code, args.duration)

    # Generate summary
    profiler.generate_summary_report()

    return 0


if __name__ == "__main__":
    sys.exit(main())
