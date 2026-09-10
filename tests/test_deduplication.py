"""Test script for deduplication functionality."""

from taparash.core.deduplication import (
    ExactDeduplicator,
    MinHashDeduplicator,
    deduplicate_exact,
    deduplicate_fuzzy,
    sha256_hash,
)


def test_exact_deduplication():
    """Test exact deduplication with SHA256."""
    print("=== Testing Exact Deduplication ===\n")

    texts = [
        "Hello world",
        "Hello world",  # Exact duplicate
        "Goodbye world",
        "Hello world",  # Another duplicate
        "Different text",
    ]

    dedup = ExactDeduplicator()
    print("Using ExactDeduplicator class:")
    for i, text in enumerate(texts):
        is_unique = dedup.add(text, index=i)
        print(f"  Text {i}: '{text}' - {'UNIQUE' if is_unique else 'DUPLICATE'}")

    print(f"\nDuplicate groups: {dedup.get_duplicate_groups()}")
    print(f"Total unique: {len(dedup.seen_hashes)}")

    unique_texts, kept_indices = deduplicate_exact(texts)
    print(f"\nUsing deduplicate_exact function:")
    print(f"  Original count: {len(texts)}")
    print(f"  Unique count: {len(unique_texts)}")
    print(f"  Kept indices: {kept_indices}")
    print(f"  Unique texts: {unique_texts}")


def test_fuzzy_deduplication():
    """Test fuzzy deduplication with MinHash."""
    print("\n\n=== Testing Fuzzy Deduplication ===\n")

    texts = [
        "The quick brown fox jumps over the lazy dog",
        "The quick brown fox jumped over the lazy dog",  # Very similar
        "A completely different sentence here",
        "The quick brown fox jumps over the lazy cat",  # Similar but different
        "Python is a great programming language",
        "Python is an excellent programming language",  # Similar
    ]

    dedup = MinHashDeduplicator(
        num_perm=128,
        threshold=0.8,
        shingle_size=3,
        use_word_shingles=True,
    )

    print("Using MinHashDeduplicator class (threshold=0.8):")
    for i, text in enumerate(texts):
        is_unique, similar_idx = dedup.add(text)
        if is_unique:
            print(f"  Text {i}: UNIQUE - '{text[:50]}...'")
        else:
            print(f"  Text {i}: SIMILAR to text {similar_idx} - '{text[:50]}...'")

    print("\n\nUsing deduplicate_fuzzy function:")
    unique_texts, kept_indices = deduplicate_fuzzy(
        texts,
        threshold=0.8,
        num_perm=128,
        shingle_size=3,
        use_word_shingles=True,
    )

    print(f"  Original count: {len(texts)}")
    print(f"  Unique count: {len(unique_texts)}")
    print(f"  Kept indices: {kept_indices}")
    print(f"\nUnique texts:")
    for idx, text in zip(kept_indices, unique_texts):
        print(f"    [{idx}] {text}")


def test_hash_function():
    """Test SHA256 hash function."""
    print("\n\n=== Testing SHA256 Hash ===\n")

    text1 = "Hello world"
    text2 = "Hello world"
    text3 = "hello world"

    hash1 = sha256_hash(text1)
    hash2 = sha256_hash(text2)
    hash3 = sha256_hash(text3)

    print(f"Text 1: '{text1}'")
    print(f"  Hash: {hash1}")
    print(f"\nText 2: '{text2}'")
    print(f"  Hash: {hash2}")
    print(f"  Same as text 1? {hash1 == hash2}")
    print(f"\nText 3: '{text3}' (lowercase)")
    print(f"  Hash: {hash3}")
    print(f"  Same as text 1? {hash1 == hash3}")


if __name__ == "__main__":
    test_hash_function()
    test_exact_deduplication()
    test_fuzzy_deduplication()
