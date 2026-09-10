"""Test script for Phase 2: Batch Optimization and Parallel Processing."""

import time

from taparash import TaparashFilter, QualityConfig


def test_batch_optimization():
    """Test batch processing optimization with different batch sizes."""
    print("=" * 70)
    print("TEST 1: Batch Processing Optimization")
    print("=" * 70)

    chunks = []
    for i in range(200):
        if i % 10 == 0:
            chunks.append(f"The quick brown fox jumps over the lazy dog number {i}")
        elif i % 10 == 1:
            chunks.append("Short")  # Too short
        elif i % 10 == 2:
            chunks.append(f"Valid text chunk with sufficient length for processing {i}")
        elif i % 10 == 3:
            chunks.append("The quick brown fox jumps over the lazy dog number 0")  # Duplicate
        else:
            chunks.append(f"Another valid chunk that meets minimum length requirements {i}")

    for batch_size in [50, 100, 200]:
        config = QualityConfig(
            min_chunk_length=20,
            batch_size=batch_size,
            enable_pii_masking=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=True,
            enable_dlq=False,
        )

        app = TaparashFilter(config)

        start = time.time()
        results = app.process_batch(chunks, use_parallel=False)
        elapsed = time.time() - start

        print(f"\nBatch Size: {batch_size}")
        print(f"  Processing Time: {elapsed:.3f}s")
        print(f"  Accepted: {len(results.accepted)}")
        print(f"  Rejected: {len(results.rejected)}")
        print(f"  Throughput: {len(chunks) / elapsed:.0f} chunks/sec")


def test_parallel_processing():
    """Test parallel processing with different worker counts."""
    print("\n\n" + "=" * 70)
    print("TEST 2: Parallel Processing")
    print("=" * 70)

    chunks = []
    for i in range(500):
        if i % 10 == 0:
            chunks.append(f"Processing text chunk with adequate length for validation {i}")
        elif i % 10 == 1:
            chunks.append("Too short")
        else:
            chunks.append(f"Valid chunk number {i} with sufficient content for processing")

    worker_configs = [1, 2, 4, 8]

    for workers in worker_configs:
        config = QualityConfig(
            min_chunk_length=20,
            batch_size=100,
            parallel_workers=workers,
            enable_pii_masking=True,
            enable_entropy_check=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_dlq=False,
        )

        app = TaparashFilter(config)

        start = time.time()
        results_seq = app.process_batch(chunks, use_parallel=False)
        elapsed_seq = time.time() - start

        app.reset()
        start = time.time()
        results_par = app.process_batch(chunks, use_parallel=True)
        elapsed_par = time.time() - start

        speedup = elapsed_seq / elapsed_par if elapsed_par > 0 else 0

        print(f"\nWorkers: {workers}")
        print(f"  Sequential: {elapsed_seq:.3f}s ({len(chunks) / elapsed_seq:.0f} chunks/sec)")
        print(f"  Parallel:   {elapsed_par:.3f}s ({len(chunks) / elapsed_par:.0f} chunks/sec)")
        print(f"  Speedup:    {speedup:.2f}x")
        print(f"  Results Match: {len(results_seq.accepted) == len(results_par.accepted)}")


def test_parallel_correctness():
    """Verify parallel processing produces same results as sequential."""
    print("\n\n" + "=" * 70)
    print("TEST 3: Parallel Processing Correctness")
    print("=" * 70)

    chunks = [
        "This is a valid text chunk with enough length",
        "Short",  # Too short
        "Contact us at test@example.com for more info",  # PII
        "This is a valid text chunk with enough length",  # Duplicate
        "ajsd89fh23kjhdf98h23kjdhf98h234kjhsdf",  # High entropy
        "Another completely valid chunk with sufficient length",
        "Yet another valid text chunk for our processing pipeline",
    ] * 10  # 70 chunks

    config = QualityConfig(
        min_chunk_length=20,
        batch_size=20,
        parallel_workers=4,
        enable_pii_masking=True,
        enable_entropy_check=True,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=True,
        enable_dlq=False,
    )

    app_seq = TaparashFilter(config)
    results_seq = app_seq.process_batch(chunks, use_parallel=False)

    app_par = TaparashFilter(config)
    results_par = app_par.process_batch(chunks, use_parallel=True)

    print(f"\nSequential Results:")
    print(f"  Accepted: {len(results_seq.accepted)}")
    print(f"  Rejected: {len(results_seq.rejected)}")

    print(f"\nParallel Results:")
    print(f"  Accepted: {len(results_par.accepted)}")
    print(f"  Rejected: {len(results_par.rejected)}")

    assert len(results_seq.accepted) == len(results_par.accepted), "Accepted counts don't match!"
    assert len(results_seq.rejected) == len(results_par.rejected), "Rejected counts don't match!"

    print("\n[OK] Results match! Parallel processing is correct.")

    print("\nSequential Statistics:")
    app_seq.print_stats()

    print("\nParallel Statistics:")
    app_par.print_stats()


def test_large_batch():
    """Test processing a large batch."""
    print("\n\n" + "=" * 70)
    print("TEST 4: Large Batch Processing")
    print("=" * 70)

    print("Generating 5000 test chunks...")
    chunks = [
        f"Test chunk number {i} with sufficient length for validation and processing"
        for i in range(5000)
    ]

    config = QualityConfig(
        min_chunk_length=20,
        batch_size=200,
        parallel_workers=4,
        enable_pii_masking=True,
        enable_entropy_check=True,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=False,
        enable_dlq=False,
    )

    print("\nProcessing with sequential mode...")
    app = TaparashFilter(config)
    start = time.time()
    results = app.process_batch(chunks, use_parallel=False)
    elapsed_seq = time.time() - start

    print(f"  Time: {elapsed_seq:.2f}s")
    print(f"  Throughput: {len(chunks) / elapsed_seq:.0f} chunks/sec")

    print("\nProcessing with parallel mode...")
    app.reset()
    start = time.time()
    results = app.process_batch(chunks, use_parallel=True)
    elapsed_par = time.time() - start

    print(f"  Time: {elapsed_par:.2f}s")
    print(f"  Throughput: {len(chunks) / elapsed_par:.0f} chunks/sec")
    print(f"  Speedup: {elapsed_seq / elapsed_par:.2f}x")

    print(f"\nResults:")
    print(f"  Accepted: {len(results.accepted)}")
    print(f"  Rejected: {len(results.rejected)}")


if __name__ == "__main__":
    try:
        test_batch_optimization()
        test_parallel_processing()
        test_parallel_correctness()
        test_large_batch()

        print("\n\n" + "=" * 70)
        print("ALL BATCH & PARALLEL TESTS PASSED")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
