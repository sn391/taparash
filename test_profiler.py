"""Test script for performance profiling tools."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import QualityConfig
from pipeline import TaparashFilter
from profiler import TaparashProfiler, benchmark_pipeline, compare_configurations, profile_comparison


def test_basic_profiler():
    """Test basic profiler functionality."""
    print("=" * 70)
    print("TEST 1: Basic Profiler Usage")
    print("=" * 70)

    profiler = TaparashProfiler(enabled=True)

    # Simulate gate execution
    import time

    with profiler.profile_gate("Gate 1: Length Check"):
        time.sleep(0.001)

    with profiler.profile_gate("Gate 2: PII Masking"):
        time.sleep(0.002)

    with profiler.profile_gate("Gate 3: Entropy Check"):
        time.sleep(0.0015)

    # Multiple calls to same gate
    for _ in range(5):
        with profiler.profile_gate("Gate 4: Deduplication"):
            time.sleep(0.0005)

    profiler.report.total_chunks = 10
    profiler.report.total_time = 0.015

    print()
    profiler.print_report()
    print()


def test_benchmark_pipeline():
    """Test pipeline benchmarking."""
    print("\n" + "=" * 70)
    print("TEST 2: Pipeline Benchmarking")
    print("=" * 70)

    # Generate test data
    test_data = [
        f"Valid text chunk number {i} with sufficient length for processing"
        for i in range(100)
    ]

    # Add some variations
    test_data.extend([
        "Short",  # Too short
        "Valid text chunk number 0 with sufficient length for processing",  # Duplicate
    ] * 5)

    def create_pipeline():
        config = QualityConfig(
            min_chunk_length=20,
            enable_pii_masking=True,
            enable_entropy_check=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_dlq=False
        )
        return TaparashFilter(config)

    print(f"\nBenchmarking with {len(test_data)} chunks...\n")
    results = benchmark_pipeline(
        pipeline_factory=create_pipeline,
        test_data=test_data,
        iterations=3,
        use_parallel=False
    )

    print("Benchmark Results:")
    print(f"  Iterations: {results['iterations']}")
    print(f"  Chunk count: {results['chunk_count']}")
    print()

    summary = results['summary']
    print(f"Performance Summary:")
    print(f"  Avg time:       {summary['avg_time_sec']:.3f}s")
    print(f"  Min time:       {summary['min_time_sec']:.3f}s")
    print(f"  Max time:       {summary['max_time_sec']:.3f}s")
    print(f"  Avg throughput: {summary['avg_throughput']:.0f} chunks/sec")
    print(f"  Min throughput: {summary['min_throughput']:.0f} chunks/sec")
    print(f"  Max throughput: {summary['max_throughput']:.0f} chunks/sec")
    print()


def test_configuration_comparison():
    """Test comparing multiple configurations."""
    print("=" * 70)
    print("TEST 3: Configuration Comparison")
    print("=" * 70)

    # Generate test data
    test_data = [
        f"Test chunk {i} with enough content to pass validation"
        for i in range(200)
    ]

    # Configuration 1: Minimal filtering
    def config_minimal():
        config = QualityConfig(
            min_chunk_length=20,
            enable_pii_masking=False,
            enable_entropy_check=False,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_dlq=False
        )
        return TaparashFilter(config)

    # Configuration 2: Standard filtering
    def config_standard():
        config = QualityConfig(
            min_chunk_length=20,
            enable_pii_masking=True,
            enable_entropy_check=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_dlq=False
        )
        return TaparashFilter(config)

    # Configuration 3: Full filtering
    def config_full():
        config = QualityConfig(
            min_chunk_length=20,
            enable_pii_masking=True,
            enable_entropy_check=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=True,
            dedup_threshold=0.85,
            enable_dlq=False
        )
        return TaparashFilter(config)

    configs = [
        ("Minimal", config_minimal),
        ("Standard", config_standard),
        ("Full", config_full),
    ]

    results = compare_configurations(configs, test_data, iterations=2)

    print("\nComparison complete!")
    print(f"Best configuration: {results['best_configuration']}")
    print()


def test_profile_comparison():
    """Test side-by-side configuration comparison."""
    print("=" * 70)
    print("TEST 4: Side-by-Side Comparison")
    print("=" * 70)

    test_data = [
        f"Chunk {i} with sufficient text content for validation"
        for i in range(150)
    ]

    def sequential_config():
        config = QualityConfig(
            min_chunk_length=20,
            batch_size=50,
            parallel_workers=4,
            enable_pii_masking=True,
            enable_entropy_check=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_dlq=False
        )
        return TaparashFilter(config)

    def parallel_config():
        config = QualityConfig(
            min_chunk_length=20,
            batch_size=50,
            parallel_workers=4,
            enable_pii_masking=True,
            enable_entropy_check=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_dlq=False
        )
        pipeline = TaparashFilter(config)
        # Override to use parallel
        original_process = pipeline.process_batch

        def parallel_process(texts, use_parallel=True):
            return original_process(texts, use_parallel=use_parallel)

        pipeline.process_batch = parallel_process
        return pipeline

    profile_comparison(
        "Sequential",
        sequential_config,
        "Parallel",
        parallel_config,
        test_data
    )


def test_profiler_json_export():
    """Test exporting profiler results to JSON."""
    print("\n" + "=" * 70)
    print("TEST 5: JSON Export")
    print("=" * 70)

    profiler = TaparashProfiler(enabled=True)

    # Simulate some gates
    import time

    for _ in range(10):
        with profiler.profile_gate("Length Check"):
            time.sleep(0.0001)

        with profiler.profile_gate("PII Masking"):
            time.sleep(0.0002)

    profiler.report.total_chunks = 10
    profiler.report.total_time = 0.003

    # Export to JSON
    output_file = "profiler_test_export.json"
    profiler.save_report(output_file)

    print(f"\nExported profile report to: {output_file}")

    # Verify file exists and print summary
    import os
    import json

    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            data = json.load(f)

        print(f"Report contains {len(data['gates'])} gates")
        print(f"Total chunks: {data['total_chunks']}")
        print(f"Throughput: {data['throughput_chunks_per_sec']:.0f} chunks/sec")

        # Cleanup
        os.remove(output_file)
        print(f"\nCleaned up {output_file}")

    print()


if __name__ == "__main__":
    try:
        test_basic_profiler()
        test_benchmark_pipeline()
        test_configuration_comparison()
        test_profile_comparison()
        test_profiler_json_export()

        print("\n" + "=" * 70)
        print("ALL PROFILER TESTS PASSED")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
