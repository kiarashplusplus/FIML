"""
Performance Regression Detection

Compares benchmarks between branches and detects regressions.

Features:
- Run benchmarks on PR branch
- Compare with baseline from main branch
- Alert if >10% regression detected
- Track performance trends over time
- Generate comparison reports

Usage:
    # Run and compare with baseline
    python tests/performance/regression_detection.py --baseline benchmarks/baseline.json

    # Save current results as baseline
    python tests/performance/regression_detection.py --save-baseline

    # Run in CI mode (fail on regression)
    python tests/performance/regression_detection.py --ci --threshold 0.10
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class RegressionDetector:
    """Detect performance regressions by comparing benchmarks"""

    def __init__(self, threshold: float = 0.10):
        """
        Args:
            threshold: Regression threshold (default: 10%)
        """
        self.threshold = threshold
        self.regressions: List[Dict] = []
        self.improvements: List[Dict] = []

    def run_benchmarks(self, output_file: str = "benchmark_results.json") -> Dict:
        """Run pytest benchmarks and save results"""
        print("Running benchmarks...")

        cmd = [
            "pytest",
            "benchmarks/",
            "--benchmark-only",
            "--benchmark-json=" + output_file,
            "-v"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Benchmark run failed: {result.stderr}")
            return {}

        # Load results
        with open(output_file, 'r') as f:
            return json.load(f)

    def load_results(self, filepath: str) -> Optional[Dict]:
        """Load benchmark results from file"""
        path = Path(filepath)
        if not path.exists():
            print(f"Results file not found: {filepath}")
            return None

        with open(filepath, 'r') as f:
            return json.load(f)

    def compare_benchmarks(
        self,
        current: Dict,
        baseline: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Compare current benchmarks with baseline

        Returns:
            (regressions, improvements)
        """
        regressions = []
        improvements = []

        current_benchmarks = {
            b['name']: b for b in current.get('benchmarks', [])
        }
        baseline_benchmarks = {
            b['name']: b for b in baseline.get('benchmarks', [])
        }

        for name, current_bench in current_benchmarks.items():
            if name not in baseline_benchmarks:
                print(f"New benchmark: {name}")
                continue

            baseline_bench = baseline_benchmarks[name]

            # Compare mean execution time
            current_mean = current_bench['stats']['mean']
            baseline_mean = baseline_bench['stats']['mean']

            change = (current_mean - baseline_mean) / baseline_mean

            comparison = {
                'name': name,
                'current_mean': current_mean,
                'baseline_mean': baseline_mean,
                'change_percent': change * 100,
                'change_abs': current_mean - baseline_mean,
            }

            if change > self.threshold:
                # Regression detected
                regressions.append(comparison)
            elif change < -self.threshold:
                # Improvement detected
                improvements.append(comparison)

        self.regressions = regressions
        self.improvements = improvements

        return regressions, improvements

    def generate_report(self) -> str:
        """Generate regression report"""
        report = []
        report.append("=" * 80)
        report.append("PERFORMANCE REGRESSION DETECTION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Threshold: {self.threshold * 100:.0f}%")
        report.append("")

        if self.regressions:
            report.append(f"⚠️  REGRESSIONS DETECTED: {len(self.regressions)}")
            report.append("-" * 80)
            for reg in self.regressions:
                report.append(f"\nBenchmark: {reg['name']}")
                report.append(f"  Baseline: {reg['baseline_mean']*1000:.2f}ms")
                report.append(f"  Current:  {reg['current_mean']*1000:.2f}ms")
                report.append(f"  Change:   {reg['change_percent']:+.2f}% ({reg['change_abs']*1000:+.2f}ms)")
            report.append("")
        else:
            report.append("✓ No regressions detected")
            report.append("")

        if self.improvements:
            report.append(f"✓ IMPROVEMENTS DETECTED: {len(self.improvements)}")
            report.append("-" * 80)
            for imp in self.improvements:
                report.append(f"\nBenchmark: {imp['name']}")
                report.append(f"  Baseline: {imp['baseline_mean']*1000:.2f}ms")
                report.append(f"  Current:  {imp['current_mean']*1000:.2f}ms")
                report.append(f"  Change:   {imp['change_percent']:+.2f}% ({imp['change_abs']*1000:+.2f}ms)")
            report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self, filepath: str):
        """Save report to file"""
        report = self.generate_report()
        with open(filepath, 'w') as f:
            f.write(report)
        print(f"Report saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Performance regression detection")
    parser.add_argument(
        '--baseline',
        type=str,
        help='Path to baseline benchmark results (JSON)'
    )
    parser.add_argument(
        '--current',
        type=str,
        default='benchmark_results.json',
        help='Path to current benchmark results (default: benchmark_results.json)'
    )
    parser.add_argument(
        '--save-baseline',
        action='store_true',
        help='Run benchmarks and save as baseline'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.10,
        help='Regression threshold (default: 0.10 = 10%%)'
    )
    parser.add_argument(
        '--ci',
        action='store_true',
        help='CI mode: fail if regressions detected'
    )
    parser.add_argument(
        '--report',
        type=str,
        default='regression_report.txt',
        help='Output report file'
    )

    args = parser.parse_args()

    detector = RegressionDetector(threshold=args.threshold)

    if args.save_baseline:
        # Run benchmarks and save as baseline
        print("Running benchmarks and saving as baseline...")
        results = detector.run_benchmarks("benchmark_baseline.json")
        if results:
            print("Baseline saved to: benchmark_baseline.json")
            return 0
        else:
            print("Failed to run benchmarks")
            return 1

    # Run current benchmarks
    print("Running current benchmarks...")
    current_results = detector.run_benchmarks(args.current)

    if not current_results:
        print("Failed to run current benchmarks")
        return 1

    # Load baseline
    if not args.baseline:
        print("No baseline provided. Use --baseline to compare.")
        print(f"To create baseline: python {sys.argv[0]} --save-baseline")
        return 0

    print(f"Loading baseline from: {args.baseline}")
    baseline_results = detector.load_results(args.baseline)

    if not baseline_results:
        print("Failed to load baseline")
        return 1

    # Compare
    print("Comparing benchmarks...")
    regressions, improvements = detector.compare_benchmarks(
        current_results,
        baseline_results
    )

    # Generate report
    report = detector.generate_report()
    print("\n" + report)

    # Save report
    detector.save_report(args.report)

    # CI mode: fail if regressions detected
    if args.ci and regressions:
        print(f"\n❌ CI FAILURE: {len(regressions)} performance regressions detected")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
