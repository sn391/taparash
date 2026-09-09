"""Performance profiling tools for Taparash pipeline."""

import time
import json
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager


@dataclass
class GateProfile:
    """Performance profile for a single gate."""

    name: str
    total_time: float = 0.0
    call_count: int = 0
    min_time: float = float('inf')
    max_time: float = 0.0

    @property
    def avg_time(self) -> float:
        """Average time per call."""
        return self.total_time / self.call_count if self.call_count > 0 else 0.0

    def record(self, elapsed: float):
        """Record a single execution time."""
        self.total_time += elapsed
        self.call_count += 1
        self.min_time = min(self.min_time, elapsed)
        self.max_time = max(self.max_time, elapsed)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'total_time_ms': self.total_time * 1000,
            'call_count': self.call_count,
            'avg_time_ms': self.avg_time * 1000,
            'min_time_ms': self.min_time * 1000 if self.min_time != float('inf') else 0,
            'max_time_ms': self.max_time * 1000,
        }


@dataclass
class ProfileReport:
    """Complete performance profile report."""

    total_time: float = 0.0
    total_chunks: int = 0
    gates: Dict[str, GateProfile] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def throughput(self) -> float:
        """Chunks per second."""
        return self.total_chunks / self.total_time if self.total_time > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_time_sec': self.total_time,
            'total_chunks': self.total_chunks,
            'throughput_chunks_per_sec': self.throughput,
            'gates': {name: gate.to_dict() for name, gate in self.gates.items()}
        }

    def print_report(self):
        """Print formatted performance report."""
        print("=" * 70)
        print("TAPARASH PERFORMANCE PROFILE")
        print("=" * 70)
        print(f"Total Time:    {self.total_time:.3f}s")
        print(f"Total Chunks:  {self.total_chunks}")
        print(f"Throughput:    {self.throughput:.0f} chunks/sec")
        print()

        print("Gate Performance:")
        print(f"{'Gate':<30} {'Calls':<8} {'Total (ms)':<12} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12}")
        print("-" * 70)

        # Sort by total time descending
        sorted_gates = sorted(
            self.gates.values(),
            key=lambda g: g.total_time,
            reverse=True
        )

        for gate in sorted_gates:
            print(
                f"{gate.name:<30} "
                f"{gate.call_count:<8} "
                f"{gate.total_time * 1000:<12.2f} "
                f"{gate.avg_time * 1000:<12.2f} "
                f"{gate.min_time * 1000 if gate.min_time != float('inf') else 0:<12.2f} "
                f"{gate.max_time * 1000:<12.2f}"
            )

        print("=" * 70)

    def save_json(self, filepath: str):
        """Save report to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class TaparashProfiler:
    """
    Performance profiler for Taparash pipeline.

    Measures execution time for each gate and provides detailed reports.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize profiler.

        Args:
            enabled: Whether profiling is active (default: True)
        """
        self.enabled = enabled
        self.report = ProfileReport()
        self._current_gate_stack: List[tuple] = []

    @contextmanager
    def profile_gate(self, gate_name: str):
        """
        Context manager to profile a gate.

        Args:
            gate_name: Name of the gate to profile

        Usage:
            with profiler.profile_gate("Gate 1: Length"):
                # ... gate logic ...
                pass
        """
        if not self.enabled:
            yield
            return

        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time

            # Get or create gate profile
            if gate_name not in self.report.gates:
                self.report.gates[gate_name] = GateProfile(name=gate_name)

            self.report.gates[gate_name].record(elapsed)

    def start_batch(self):
        """Start profiling a batch."""
        if self.enabled:
            self.report.start_time = time.perf_counter()

    def end_batch(self, chunk_count: int):
        """
        End profiling a batch.

        Args:
            chunk_count: Number of chunks processed
        """
        if self.enabled and self.report.start_time:
            self.report.end_time = time.perf_counter()
            self.report.total_time = self.report.end_time - self.report.start_time
            self.report.total_chunks = chunk_count

    def reset(self):
        """Reset profiler statistics."""
        self.report = ProfileReport()
        self._current_gate_stack.clear()

    def get_report(self) -> ProfileReport:
        """Get current profile report."""
        return self.report

    def print_report(self):
        """Print formatted performance report."""
        self.report.print_report()

    def save_report(self, filepath: str):
        """Save report to JSON file."""
        self.report.save_json(filepath)


def benchmark_pipeline(
    pipeline_factory: Callable,
    test_data: List[str],
    iterations: int = 3,
    use_parallel: bool = False
) -> Dict:
    """
    Benchmark a pipeline configuration.

    Args:
        pipeline_factory: Function that returns a configured TaparashFilter
        test_data: List of text chunks to process
        iterations: Number of iterations to run
        use_parallel: Whether to use parallel processing

    Returns:
        Dictionary with benchmark results
    """
    results = {
        'iterations': iterations,
        'chunk_count': len(test_data),
        'use_parallel': use_parallel,
        'runs': []
    }

    for i in range(iterations):
        pipeline = pipeline_factory()

        start = time.perf_counter()
        batch_result = pipeline.process_batch(test_data, use_parallel=use_parallel)
        elapsed = time.perf_counter() - start

        throughput = len(test_data) / elapsed

        run_result = {
            'iteration': i + 1,
            'elapsed_sec': elapsed,
            'throughput_chunks_per_sec': throughput,
            'accepted': len(batch_result.accepted),
            'rejected': len(batch_result.rejected),
        }
        results['runs'].append(run_result)

    # Calculate statistics
    times = [r['elapsed_sec'] for r in results['runs']]
    throughputs = [r['throughput_chunks_per_sec'] for r in results['runs']]

    results['summary'] = {
        'avg_time_sec': sum(times) / len(times),
        'min_time_sec': min(times),
        'max_time_sec': max(times),
        'avg_throughput': sum(throughputs) / len(throughputs),
        'min_throughput': min(throughputs),
        'max_throughput': max(throughputs),
    }

    return results


def compare_configurations(
    configs: List[tuple],  # List of (name, pipeline_factory) tuples
    test_data: List[str],
    iterations: int = 3
) -> Dict:
    """
    Compare multiple pipeline configurations.

    Args:
        configs: List of (name, pipeline_factory) tuples
        test_data: Test data to process
        iterations: Iterations per configuration

    Returns:
        Dictionary with comparison results
    """
    results = {
        'test_chunk_count': len(test_data),
        'iterations': iterations,
        'configurations': []
    }

    print("=" * 70)
    print("CONFIGURATION COMPARISON")
    print("=" * 70)
    print(f"Test data: {len(test_data)} chunks")
    print(f"Iterations: {iterations}\n")

    for name, factory in configs:
        print(f"Testing: {name}...")
        benchmark = benchmark_pipeline(factory, test_data, iterations)

        config_result = {
            'name': name,
            'benchmark': benchmark
        }
        results['configurations'].append(config_result)

        summary = benchmark['summary']
        print(f"  Avg time:       {summary['avg_time_sec']:.3f}s")
        print(f"  Avg throughput: {summary['avg_throughput']:.0f} chunks/sec")
        print()

    # Find best configuration
    best_config = max(
        results['configurations'],
        key=lambda c: c['benchmark']['summary']['avg_throughput']
    )

    results['best_configuration'] = best_config['name']

    print(f"Best configuration: {best_config['name']}")
    print("=" * 70)

    return results


def profile_comparison(
    config1_name: str,
    config1_factory: Callable,
    config2_name: str,
    config2_factory: Callable,
    test_data: List[str]
) -> None:
    """
    Compare two configurations side-by-side.

    Args:
        config1_name: Name of first configuration
        config1_factory: Factory for first pipeline
        config2_name: Name of second configuration
        config2_factory: Factory for second pipeline
        test_data: Test data to process
    """
    print("=" * 70)
    print(f"COMPARING: {config1_name} vs {config2_name}")
    print("=" * 70)
    print(f"Test data: {len(test_data)} chunks\n")

    # Run config 1
    print(f"Running {config1_name}...")
    pipeline1 = config1_factory()
    start1 = time.perf_counter()
    results1 = pipeline1.process_batch(test_data)
    elapsed1 = time.perf_counter() - start1
    throughput1 = len(test_data) / elapsed1

    # Run config 2
    print(f"Running {config2_name}...")
    pipeline2 = config2_factory()
    start2 = time.perf_counter()
    results2 = pipeline2.process_batch(test_data)
    elapsed2 = time.perf_counter() - start2
    throughput2 = len(test_data) / elapsed2

    # Compare
    speedup = elapsed1 / elapsed2

    print()
    print(f"{'Metric':<30} {config1_name:<20} {config2_name:<20}")
    print("-" * 70)
    print(f"{'Time (sec)':<30} {elapsed1:<20.3f} {elapsed2:<20.3f}")
    print(f"{'Throughput (chunks/sec)':<30} {throughput1:<20.0f} {throughput2:<20.0f}")
    print(f"{'Accepted':<30} {len(results1.accepted):<20} {len(results2.accepted):<20}")
    print(f"{'Rejected':<30} {len(results1.rejected):<20} {len(results2.rejected):<20}")
    print()
    print(f"Speedup: {speedup:.2f}x ({'faster' if speedup > 1 else 'slower'})")
    print("=" * 70)
