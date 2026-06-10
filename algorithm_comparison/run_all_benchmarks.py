"""
Master script to run all benchmarks sequentially or in parallel.
Includes progress bar and ETA tracking.
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import timedelta
from typing import List, Dict, Tuple


class ProgressBar:
    """Simple progress bar with ETA"""

    def __init__(self, total: int, width: int = 50):
        self.total = total
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, increment: int = 1):
        self.current += increment
        elapsed = time.time() - self.start_time

        if self.current > 0:
            eta_seconds = (elapsed / self.current) * (self.total - self.current)
            eta = str(timedelta(seconds=int(eta_seconds)))
        else:
            eta = "calculating..."

        progress = self.current / self.total
        filled = int(self.width * progress)
        bar = '█' * filled + '░' * (self.width - filled)

        percent = progress * 100
        print(f'\r[{bar}] {percent:.1f}% | {self.current}/{self.total} | ETA: {eta}', end='', flush=True)

        if self.current >= self.total:
            print()  # New line when complete


def run_benchmark(script_path: Path) -> Tuple[str, bool, str, float]:
    """
    Run a single benchmark script.

    Returns:
        (script_name, success, output, duration)
    """
    script_name = script_path.name
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout per benchmark
            cwd=script_path.parent
        )
        duration = time.time() - start_time

        success = result.returncode == 0
        output = result.stdout if success else result.stderr

        return (script_name, success, output, duration)

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return (script_name, False, "TIMEOUT: Exceeded 1 hour", duration)

    except Exception as e:
        duration = time.time() - start_time
        return (script_name, False, f"ERROR: {str(e)}", duration)


def find_benchmark_scripts(base_dir: Path) -> List[Path]:
    """Find all benchmark scripts in the directory"""
    patterns = [
        'benchmark_*.py',
        '*_benchmark.py',
        'test_*.py',
        'run_*.py'
    ]

    scripts = []
    for pattern in patterns:
        scripts.extend(base_dir.glob(pattern))

    # Remove this master script from the list
    scripts = [s for s in scripts if s.name != 'run_all_benchmarks.py']

    return sorted(set(scripts))


def run_sequential(scripts: List[Path], verbose: bool = False) -> Dict:
    """Run benchmarks sequentially with progress tracking"""
    print(f"\n{'='*70}")
    print(f"Running {len(scripts)} benchmarks SEQUENTIALLY")
    print(f"{'='*70}\n")

    results = {
        'total': len(scripts),
        'passed': 0,
        'failed': 0,
        'details': []
    }

    progress = ProgressBar(len(scripts))

    for script in scripts:
        if verbose:
            print(f"\n\nRunning: {script.name}")
            print("-" * 70)

        script_name, success, output, duration = run_benchmark(script)

        results['details'].append({
            'script': script_name,
            'success': success,
            'duration': duration,
            'output': output
        })

        if success:
            results['passed'] += 1
        else:
            results['failed'] += 1

        if verbose:
            print(output)
            print(f"\nStatus: {'✓ PASSED' if success else '✗ FAILED'}")
            print(f"Duration: {duration:.2f}s")

        progress.update()

    return results


def run_parallel(scripts: List[Path], max_workers: int = None, verbose: bool = False) -> Dict:
    """Run benchmarks in parallel with progress tracking"""
    if max_workers is None:
        import os
        max_workers = min(len(scripts), os.cpu_count() or 4)

    print(f"\n{'='*70}")
    print(f"Running {len(scripts)} benchmarks in PARALLEL (workers={max_workers})")
    print(f"{'='*70}\n")

    results = {
        'total': len(scripts),
        'passed': 0,
        'failed': 0,
        'details': []
    }

    progress = ProgressBar(len(scripts))

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_script = {executor.submit(run_benchmark, script): script for script in scripts}

        for future in as_completed(future_to_script):
            script = future_to_script[future]

            try:
                script_name, success, output, duration = future.result()

                results['details'].append({
                    'script': script_name,
                    'success': success,
                    'duration': duration,
                    'output': output
                })

                if success:
                    results['passed'] += 1
                else:
                    results['failed'] += 1

                if verbose:
                    print(f"\n\n{script_name}: {'✓ PASSED' if success else '✗ FAILED'} ({duration:.2f}s)")
                    if not success:
                        print(output)

            except Exception as e:
                results['details'].append({
                    'script': script.name,
                    'success': False,
                    'duration': 0,
                    'output': f"Exception: {str(e)}"
                })
                results['failed'] += 1

            progress.update()

    # Sort results by script name for consistent output
    results['details'].sort(key=lambda x: x['script'])

    return results


def print_summary(results: Dict, total_duration: float):
    """Print summary of benchmark results"""
    print(f"\n\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}\n")

    print(f"Total benchmarks: {results['total']}")
    print(f"Passed: {results['passed']} ✓")
    print(f"Failed: {results['failed']} ✗")
    print(f"Success rate: {(results['passed']/results['total']*100):.1f}%")
    print(f"Total duration: {timedelta(seconds=int(total_duration))}")

    print(f"\n{'='*70}")
    print("INDIVIDUAL RESULTS")
    print(f"{'='*70}\n")

    for detail in results['details']:
        status = "✓ PASS" if detail['success'] else "✗ FAIL"
        duration_str = f"{detail['duration']:.2f}s"
        print(f"{status:8} {detail['script']:40} {duration_str:>10}")

    if results['failed'] > 0:
        print(f"\n{'='*70}")
        print("FAILED BENCHMARK DETAILS")
        print(f"{'='*70}\n")

        for detail in results['details']:
            if not detail['success']:
                print(f"\n{detail['script']}:")
                print("-" * 70)
                print(detail['output'][:500])  # First 500 chars
                if len(detail['output']) > 500:
                    print("... (truncated)")
                print()


def main():
    parser = argparse.ArgumentParser(
        description='Run all benchmark scripts with progress tracking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run sequentially with progress bar
  python run_all_benchmarks.py

  # Run in parallel with 4 workers
  python run_all_benchmarks.py --parallel --workers 4

  # Run with verbose output
  python run_all_benchmarks.py --verbose

  # Run only specific pattern
  python run_all_benchmarks.py --pattern "benchmark_*.py"
        """
    )

    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run benchmarks in parallel instead of sequentially'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: CPU count)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print verbose output from each benchmark'
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default=None,
        help='Glob pattern to filter benchmark scripts (e.g., "benchmark_*.py")'
    )

    parser.add_argument(
        '--dir',
        type=str,
        default=None,
        help='Directory containing benchmark scripts (default: current directory)'
    )

    args = parser.parse_args()

    # Determine base directory
    if args.dir:
        base_dir = Path(args.dir).resolve()
    else:
        base_dir = Path(__file__).parent

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        sys.exit(1)

    # Find benchmark scripts
    if args.pattern:
        scripts = sorted(base_dir.glob(args.pattern))
        scripts = [s for s in scripts if s.name != 'run_all_benchmarks.py']
    else:
        scripts = find_benchmark_scripts(base_dir)

    if not scripts:
        print(f"No benchmark scripts found in {base_dir}")
        sys.exit(1)

    print(f"Found {len(scripts)} benchmark scripts in {base_dir}")
    if args.verbose:
        for script in scripts:
            print(f"  - {script.name}")

    # Run benchmarks
    start_time = time.time()

    if args.parallel:
        results = run_parallel(scripts, args.workers, args.verbose)
    else:
        results = run_sequential(scripts, args.verbose)

    total_duration = time.time() - start_time

    # Print summary
    print_summary(results, total_duration)

    # Exit with appropriate code
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
