"""Test script for Taparash pipeline (Priority 1 features)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from taparash import TaparashFilter, QualityConfig


def test_basic_pipeline():
    """Test basic pipeline with default configuration."""
    print("=" * 70)
    print("TEST 1: Basic Pipeline with Default Config")
    print("=" * 70)

    config = QualityConfig(
        min_chunk_length=20,
        max_chunk_length=2000,
        entropy_threshold=4.2,
        enable_pii_masking=True,
    )

    app = TaparashFilter(config=config)

    chunks = [
        "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.",
        "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.",  # Duplicate
        "This is a completely different piece of text.",
        "Contact me at john.doe@example.com for more information.",  # PII
    ]

    print(f"\nProcessing {len(chunks)} chunks...\n")

    results = app.process_batch(chunks)

    print(f"OK Accepted: {len(results.accepted)}")
    print(f"X Rejected: {len(results.rejected)}")
    print()

    for i, result in enumerate(results.accepted, 1):
        print(f"Accepted #{i}:")
        print(f"  Original: {result.original_text[:60]}...")
        print(f"  Processed: {result.text[:60]}...")
        print(f"  Metadata: {result.metadata}")
        print()

    for i, result in enumerate(results.rejected, 1):
        print(f"Rejected #{i}:")
        print(f"  Text: {result.text[:60]}...")
        print(f"  Reason: {result.reason_code}")
        print(f"  Detail: {result.reason_detail}")
        print()

    app.print_stats()


def test_pii_masking():
    """Test PII masking functionality."""
    print("\n\n" + "=" * 70)
    print("TEST 2: PII Masking")
    print("=" * 70)

    config = QualityConfig(
        min_chunk_length=10,
        enable_pii_masking=True,
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
    )

    app = TaparashFilter(config=config)

    test_cases = [
        "Email me at alice@company.com for details",
        "Call me at 555-123-4567 or (555) 987-6543",
        "My credit card is 4532-1488-0343-6467",
        "SSN: 123-45-6789 for verification",
        "Multiple PII: john@test.com and 555-0000 and 4111111111111111",
    ]

    print("\nTesting PII detection and masking:\n")

    for i, text in enumerate(test_cases, 1):
        result = app.process_single(text)
        print(f"Test #{i}:")
        print(f"  Original:  {result.original_text}")
        print(f"  Masked:    {result.text}")
        print(f"  PII Count: {result.metadata.get('pii_masked_count', 0)}")
        print(f"  Status:    {'OK ACCEPTED' if result.is_valid else 'X REJECTED'}")
        print()


def test_entropy_filtering():
    """Test entropy-based gibberish detection."""
    print("\n\n" + "=" * 70)
    print("TEST 3: Entropy Filtering (Gibberish Detection)")
    print("=" * 70)

    config = QualityConfig(
        min_chunk_length=10,
        entropy_threshold=4.2,
        enable_entropy_check=True,
        enable_pii_masking=False,
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
    )

    app = TaparashFilter(config=config)

    test_cases = [
        ("Valid English text with normal entropy", True),
        ("a8f9#$s82kjsdf092348572390485723904857239048572390485", False),
        ("JKHSDFJKHSDFJKHSDFKJHSDFKJHSDFKJHSDF", False),
        ("The quick brown fox jumps over the lazy dog", True),
        ("xXxX123!@#$%^&*()_+{}|:<>?[]\\;',./`~", False),
    ]

    print("\nTesting entropy-based filtering:\n")

    for text, expected_valid in test_cases:
        result = app.process_single(text)
        entropy = result.metadata.get('entropy', 0)
        status = "OK" if result.is_valid == expected_valid else "X"

        print(f"{status} Entropy: {entropy:.2f}")
        print(f"  Text: {text[:50]}...")
        print(f"  Expected: {'ACCEPT' if expected_valid else 'REJECT'}")
        print(f"  Got:      {'ACCEPT' if result.is_valid else 'REJECT'}")
        if not result.is_valid:
            print(f"  Reason: {result.reason_code}")
        print()


def test_deduplication():
    """Test exact and fuzzy deduplication."""
    print("\n\n" + "=" * 70)
    print("TEST 4: Deduplication (Exact + Fuzzy)")
    print("=" * 70)

    config = QualityConfig(
        min_chunk_length=10,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=True,
        dedup_threshold=0.7,
        enable_entropy_check=False,
        enable_pii_masking=False,
    )

    app = TaparashFilter(config=config)

    chunks = [
        "The cat sat on the mat",
        "The cat sat on the mat",  # Exact duplicate
        "The dog sat on the mat",  # Different
        "The cat sat on the rug",  # Similar but different
        "A completely unrelated sentence about space travel",
        "The cat sat on the mat",  # Another exact duplicate
    ]

    print(f"\nProcessing {len(chunks)} chunks for deduplication:\n")

    for i, text in enumerate(chunks, 1):
        result = app.process_single(text)
        status = "OK" if result.is_valid else "X"
        print(f"{status} Chunk {i}: {text}")
        if not result.is_valid:
            print(f"  -> {result.reason_code}: {result.reason_detail}")
        print()

    print("\nFinal statistics:")
    app.print_stats()


def test_length_validation():
    """Test length validation."""
    print("\n\n" + "=" * 70)
    print("TEST 5: Length Validation")
    print("=" * 70)

    config = QualityConfig(
        min_chunk_length=20,
        max_chunk_length=100,
        enable_entropy_check=False,
        enable_pii_masking=False,
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
    )

    app = TaparashFilter(config=config)

    test_cases = [
        ("Short", False),
        ("This is exactly twenty", True),
        ("This is a valid length text that should be accepted by the filter", True),
        ("This text is way too long and exceeds the maximum allowed length for chunks which is set to 100 characters in this test configuration", False),
    ]

    print(f"\nTesting length validation (min={config.min_chunk_length}, max={config.max_chunk_length}):\n")

    for text, expected_valid in test_cases:
        result = app.process_single(text)
        status = "OK" if result.is_valid == expected_valid else "X"
        length = len(text)

        print(f"{status} Length: {length}")
        print(f"  Text: {text[:50]}...")
        print(f"  Expected: {'ACCEPT' if expected_valid else 'REJECT'}")
        print(f"  Got:      {'ACCEPT' if result.is_valid else 'REJECT'}")
        if not result.is_valid:
            print(f"  Reason: {result.reason_code}")
        print()


def test_full_pipeline():
    """Test full pipeline with all features."""
    print("\n\n" + "=" * 70)
    print("TEST 6: Full Pipeline (All Features)")
    print("=" * 70)

    config = QualityConfig(
        min_chunk_length=20,
        max_chunk_length=2000,
        entropy_threshold=4.2,
        enable_entropy_check=True,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=True,
        dedup_threshold=0.7,
        enable_pii_masking=True,
    )

    app = TaparashFilter(config=config)

    chunks = [
        "The quarterly revenue for Q3 2024 grew by 15% reaching 4.2M EUR.",
        "The quarterly revenue for Q3 2024 grew by 15% reaching 4.2M EUR.",  # Exact dup
        "Q3 revenue dropped by 50% causing major losses in the company.",
        "aslkdfjlaksdjflkajsdflkajsdflkajsdflkajsdflkajsdflkj",  # Gibberish
        "Contact sales at sales@company.com or call 555-1234-5678",  # PII
        "Short",  # Too short
        "The quarterly revenue in Q3 2024 increased by 15% to 4.2M EUR.",  # Similar
        "Machine learning models are transforming software development practices.",
        "AI and ML are transforming how we build software today.",  # Different enough
    ]

    print(f"\nProcessing {len(chunks)} chunks through full pipeline:\n")

    results = app.process_batch(chunks)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(results.summary())
    print()

    print("Accepted Chunks:")
    for i, result in enumerate(results.accepted, 1):
        print(f"  {i}. {result.text[:60]}...")
    print()

    print("Rejected Chunks:")
    for i, result in enumerate(results.rejected, 1):
        print(f"  {i}. [{result.reason_code}] {result.original_text[:50]}...")
    print()

    app.print_stats()


if __name__ == "__main__":
    test_basic_pipeline()
    test_pii_masking()
    test_entropy_filtering()
    test_deduplication()
    test_length_validation()
    test_full_pipeline()

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
