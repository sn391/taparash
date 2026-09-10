"""Test script for PR2 features: DLQ and Semantic Deduplication."""

from taparash import TaparashFilter, QualityConfig, DeadLetterQueue


def test_dlq_basic():
    """Test Dead Letter Queue basic functionality."""
    print("=" * 70)
    print("TEST 1: Dead Letter Queue - Basic Logging")
    print("=" * 70)

    config = QualityConfig(
        min_chunk_length=20,
        enable_dlq=True,
        dlq_path="test_dlq.db",
        enable_pii_masking=True,
        enable_exact_dedup=True,
    )

    app = TaparashFilter(config)

    chunks = [
        "This is a valid chunk with enough length to pass validation",
        "Short",  # Too short
        "This is a valid chunk with enough length to pass validation",  # Duplicate
        "Another valid piece of text that should be accepted by the filter",
        "Contact us at test@example.com for more info",  # Has PII
    ]

    print(f"\nProcessing {len(chunks)} chunks...\n")
    results = app.process_batch(chunks)

    print(f"Accepted: {len(results.accepted)}")
    print(f"Rejected: {len(results.rejected)}")
    print()

    dlq = DeadLetterQueue("test_dlq.db")

    print("DLQ Statistics:")
    stats = dlq.get_rejection_stats()
    for reason, count in stats.items():
        print(f"  {reason}: {count}")

    print(f"\nTotal rejections logged: {dlq.get_total_rejections()}")

    print("\nRecent rejections:")
    recent = dlq.get_recent_rejections(limit=5)
    for r in recent:
        print(f"  [{r['reason_code']}] {r['original_text'][:50]}...")

    print("\n" + "=" * 70)


def test_dlq_analysis():
    """Test DLQ analysis and reporting."""
    print("\n\n" + "=" * 70)
    print("TEST 2: Dead Letter Queue - Analysis")
    print("=" * 70)

    dlq = DeadLetterQueue("test_dlq.db")

    dlq.print_summary()

    print("\nChunks with PII detected:")
    pii_violations = dlq.get_pii_violations(limit=10)
    for v in pii_violations:
        print(f"  Original: {v['original_text'][:40]}...")
        print(f"  Masked:   {v['processed_text'][:40]}...")
        print(f"  PII Count: {v['pii_masked_count']}")
        print()

    print("=" * 70)


def test_semantic_dedup_without_model():
    """Test semantic deduplication when model not installed."""
    print("\n\n" + "=" * 70)
    print("TEST 3: Semantic Deduplication (Without Model)")
    print("=" * 70)

    try:
        config = QualityConfig(
            min_chunk_length=20,
            enable_semantic_dedup=True,
            embeddings_model_path="sentence-transformers/all-MiniLM-L6-v2",
            enable_dlq=False,
        )

        app = TaparashFilter(config)
        print("ERROR: Should have raised ImportError")

    except (ImportError, ValueError) as e:
        print(f"OK: Correctly raised error: {str(e)[:100]}")
        print("Note: Install sentence-transformers to enable semantic dedup")

    print("=" * 70)


def test_semantic_dedup_with_model():
    """Test semantic deduplication if model is available."""
    print("\n\n" + "=" * 70)
    print("TEST 4: Semantic Deduplication (With Model)")
    print("=" * 70)

    try:
        from taparash.engines import LocalEmbedder  # noqa: F401

        print("sentence-transformers is installed!")
        print("Testing semantic deduplication...\n")

        config = QualityConfig(
            min_chunk_length=20,
            enable_semantic_dedup=True,
            semantic_threshold=0.85,
            embeddings_model_path="sentence-transformers/all-MiniLM-L6-v2",
            enable_dlq=True,
            dlq_path="test_dlq_semantic.db",
            enable_exact_dedup=False,
            enable_fuzzy_dedup=False,
        )

        app = TaparashFilter(config)

        chunks = [
            "Machine learning is transforming software development",
            "AI and ML are revolutionizing how we build software",  # Semantically similar
            "The weather today is sunny and warm",
            "Artificial intelligence is changing software engineering",  # Similar to first
        ]

        print("Processing semantically similar texts:\n")
        results = app.process_batch(chunks)

        print(f"Accepted: {len(results.accepted)}")
        for i, r in enumerate(results.accepted, 1):
            print(f"  {i}. {r.text[:60]}...")

        print(f"\nRejected: {len(results.rejected)}")
        for i, r in enumerate(results.rejected, 1):
            print(f"  {i}. [{r.reason_code}] {r.text[:60]}...")
            if 'similarity_score' in r.metadata:
                print(f"      Similarity: {r.metadata['similarity_score']:.3f}")

        app.print_stats()

    except ImportError:
        print("sentence-transformers not installed.")
        print("Install with: pip install sentence-transformers")
        print("Skipping semantic deduplication test.")

    print("=" * 70)


def test_dlq_export():
    """Test DLQ export functionality."""
    print("\n\n" + "=" * 70)
    print("TEST 5: DLQ Export")
    print("=" * 70)

    dlq = DeadLetterQueue("test_dlq.db")

    output_file = "dlq_export.json"
    count = dlq.export_to_json(output_file)
    print(f"Exported {count} rejection records to {output_file}")

    output_file2 = "dlq_length_issues.json"
    count2 = dlq.export_to_json(output_file2, reason_code="LENGTH_TOO_SHORT")
    print(f"Exported {count2} LENGTH_TOO_SHORT records to {output_file2}")

    print("=" * 70)


def cleanup():
    """Clean up test database files."""
    import os

    print("\n\nCleaning up test files...")
    for file in ["test_dlq.db", "test_dlq_semantic.db", "dlq_export.json", "dlq_length_issues.json"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"  Removed {file}")


if __name__ == "__main__":
    try:
        test_dlq_basic()
        test_dlq_analysis()
        test_semantic_dedup_without_model()
        test_semantic_dedup_with_model()
        test_dlq_export()

        print("\n\n" + "=" * 70)
        print("ALL PR2 TESTS COMPLETED")
        print("=" * 70)

    finally:
        cleanup()
