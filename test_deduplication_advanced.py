"""Advanced test script for deduplication functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from taparash.core.deduplication import (
    MinHashDeduplicator,
    deduplicate_fuzzy,
)


def test_fuzzy_with_different_thresholds():
    """Test fuzzy deduplication with different thresholds."""
    print("=== Testing Fuzzy Deduplication with Different Thresholds ===\n")

    texts = [
        "The quick brown fox jumps over the lazy dog",
        "The quick brown fox jumped over the lazy dog",
        "The quick brown fox jumps over the lazy cat",
        "A completely different sentence",
        "The quick brown fox jumps over lazy dogs",
    ]

    for threshold in [0.5, 0.7, 0.9]:
        print(f"\n--- Threshold: {threshold} ---")
        dedup = MinHashDeduplicator(
            num_perm=256,
            threshold=threshold,
            shingle_size=2,
            use_word_shingles=True
        )

        kept = []
        for i, text in enumerate(texts):
            is_unique, similar_idx = dedup.add(text)
            if is_unique:
                print(f"  [{i}] KEPT: {text}")
                kept.append(i)
            else:
                print(f"  [{i}] SKIP (similar to [{similar_idx}]): {text}")

        print(f"  Kept {len(kept)}/{len(texts)} texts")


def test_character_vs_word_shingles():
    """Test character-based vs word-based shingles."""
    print("\n\n=== Character-based vs Word-based Shingles ===\n")

    texts = [
        "The cat sat on the mat",
        "The dog sat on the mat",
        "The cat sat on the rug",
    ]

    print("Character-based shingles (k=5):")
    dedup_char = MinHashDeduplicator(
        num_perm=128,
        threshold=0.7,
        shingle_size=5,
        use_word_shingles=False
    )

    for i, text in enumerate(texts):
        is_unique, similar_idx = dedup_char.add(text)
        status = "UNIQUE" if is_unique else f"SIMILAR to [{similar_idx}]"
        print(f"  [{i}] {status}: {text}")

    print("\nWord-based shingles (k=3):")
    dedup_word = MinHashDeduplicator(
        num_perm=128,
        threshold=0.7,
        shingle_size=3,
        use_word_shingles=True
    )

    for i, text in enumerate(texts):
        is_unique, similar_idx = dedup_word.add(text)
        status = "UNIQUE" if is_unique else f"SIMILAR to [{similar_idx}]"
        print(f"  [{i}] {status}: {text}")


def test_near_duplicates():
    """Test detection of near-duplicate content."""
    print("\n\n=== Testing Near-Duplicate Detection ===\n")

    texts = [
        "Machine learning is transforming technology",
        "Machine learning is transforming technology.",  # Added punctuation
        "machine learning is transforming technology",   # Lowercase
        "Machine learning transforms technology",        # Slight variation
        "Deep learning is transforming technology",      # Different term
        "Artificial intelligence is changing the world", # Different content
    ]

    # Lower threshold to catch near-duplicates
    dedup = MinHashDeduplicator(
        num_perm=256,
        threshold=0.6,
        shingle_size=2,
        use_word_shingles=True
    )

    print("Detection with threshold=0.6:")
    results = []
    for i, text in enumerate(texts):
        is_unique, similar_idx = dedup.add(text)
        results.append((i, is_unique, similar_idx))

        if is_unique:
            print(f"  [{i}] UNIQUE")
        else:
            similarity_results = dedup.find_similar(text)
            sim_score = similarity_results[0][1] if similarity_results else 0
            print(f"  [{i}] DUPLICATE of [{similar_idx}] (sim: {sim_score:.2f})")
        print(f"      '{text}'")


def test_batch_deduplication():
    """Test batch deduplication with realistic dataset."""
    print("\n\n=== Batch Deduplication Test ===\n")

    # Simulate scraped web content with duplicates
    texts = [
        "Python 3.12 released with new features",
        "Python 3.12 released with new features",  # Exact duplicate
        "Python version 3.12 has been released with improvements",  # Similar
        "JavaScript framework Vue.js updated",
        "React 19 beta now available",
        "Python 3.12 comes with new features",  # Similar to first
        "New Python release: version 3.12",  # Similar
        "TypeScript 5.0 supports decorators",
    ]

    print(f"Original dataset: {len(texts)} texts\n")

    # Exact deduplication first
    from taparash.core.deduplication import deduplicate_exact
    exact_unique, exact_indices = deduplicate_exact(texts)
    print(f"After exact dedup: {len(exact_unique)} texts (removed {len(texts) - len(exact_unique)})")

    # Fuzzy deduplication on remaining
    fuzzy_unique, fuzzy_indices = deduplicate_fuzzy(
        exact_unique,
        threshold=0.55,
        num_perm=256,
        shingle_size=2,
        use_word_shingles=True
    )

    print(f"After fuzzy dedup: {len(fuzzy_unique)} texts (removed {len(exact_unique) - len(fuzzy_unique)})")
    print(f"\nFinal unique texts:")
    for i, text in enumerate(fuzzy_unique, 1):
        print(f"  {i}. {text}")


if __name__ == "__main__":
    test_fuzzy_with_different_thresholds()
    test_character_vs_word_shingles()
    test_near_duplicates()
    test_batch_deduplication()
