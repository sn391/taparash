"""Demonstration of exact and fuzzy deduplication."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from taparash.core.deduplication import (
    ExactDeduplicator,
    MinHashDeduplicator,
    deduplicate_exact,
    deduplicate_fuzzy,
)


def main():
    print("=" * 70)
    print("DEDUPLICATION DEMONSTRATION")
    print("=" * 70)

    # Example 1: Exact Deduplication
    print("\n1. EXACT DEDUPLICATION (SHA256)")
    print("-" * 70)

    exact_texts = [
        "Hello world",
        "Hello world",
        "Goodbye world",
        "Hello world",
    ]

    unique, indices = deduplicate_exact(exact_texts)
    print(f"Input: {len(exact_texts)} texts")
    print(f"Output: {len(unique)} unique texts")
    print(f"Removed: {len(exact_texts) - len(unique)} duplicates")
    print(f"\nUnique texts:")
    for text in unique:
        print(f"  - {text}")

    # Example 2: Fuzzy Deduplication with High Similarity
    print("\n\n2. FUZZY DEDUPLICATION (MinHash) - High Threshold (0.8)")
    print("-" * 70)

    fuzzy_texts = [
        "The quick brown fox jumps",
        "The quick brown fox jumped",  # 80% similar
        "The slow brown fox jumps",    # Different
        "A quick brown fox jumps",     # Similar
    ]

    dedup = MinHashDeduplicator(
        num_perm=256,
        threshold=0.8,
        shingle_size=2,
        use_word_shingles=True
    )

    print("Processing texts:")
    for i, text in enumerate(fuzzy_texts):
        is_unique, similar_idx = dedup.add(text)
        if is_unique:
            print(f"  [{i}] KEEP: '{text}'")
        else:
            print(f"  [{i}] SKIP: '{text}' (similar to [{similar_idx}])")

    # Example 3: Finding All Similar Texts
    print("\n\n3. FINDING SIMILAR TEXTS")
    print("-" * 70)

    query = "The quick brown fox jumps"
    similar = dedup.find_similar(query)

    print(f"Query: '{query}'")
    print(f"Found {len(similar)} similar texts:")
    for idx, similarity in similar:
        print(f"  - Index {idx}: {similarity:.2%} similar")
        print(f"    Text: '{fuzzy_texts[idx]}'")

    # Example 4: Near-Duplicate Detection
    print("\n\n4. NEAR-DUPLICATE DETECTION (Threshold 0.6)")
    print("-" * 70)

    articles = [
        "AI and machine learning are transforming software development",
        "Machine learning and AI transform software engineering",  # Very similar
        "Cloud computing enables scalable applications",           # Different
        "Artificial intelligence and ML revolutionize coding",     # Similar
    ]

    dedup_low = MinHashDeduplicator(
        num_perm=256,
        threshold=0.6,
        shingle_size=2,
        use_word_shingles=True
    )

    print("Input articles:")
    kept_count = 0
    for i, text in enumerate(articles):
        is_unique, similar_idx = dedup_low.add(text)
        print(f"\n  [{i}] {text}")

        if is_unique:
            print(f"      Status: UNIQUE (kept)")
            kept_count += 1
        else:
            similar_results = dedup_low.find_similar(text)
            if similar_results:
                sim_score = similar_results[0][1]
                print(f"      Status: NEAR-DUPLICATE (similarity: {sim_score:.2%})")
                print(f"      Similar to: [{similar_idx}]")

    print(f"\nKept {kept_count}/{len(articles)} articles")

    # Example 5: Batch Processing
    print("\n\n5. BATCH PROCESSING PIPELINE")
    print("-" * 70)

    dataset = [
        "Python is a popular programming language",
        "Python is a popular programming language",  # Exact duplicate
        "Python is widely used for programming",     # Near duplicate
        "Java is an object-oriented language",
        "JavaScript runs in the browser",
        "Java is object oriented",                   # Near duplicate
    ]

    print(f"Step 1: Original dataset ({len(dataset)} texts)")

    # Step 1: Remove exact duplicates
    exact_unique, _ = deduplicate_exact(dataset)
    print(f"Step 2: After exact dedup ({len(exact_unique)} texts)")

    # Step 2: Remove fuzzy duplicates
    fuzzy_unique, kept_idx = deduplicate_fuzzy(
        exact_unique,
        threshold=0.6,
        num_perm=256,
        shingle_size=2,
        use_word_shingles=True
    )
    print(f"Step 3: After fuzzy dedup ({len(fuzzy_unique)} texts)")

    print(f"\nFinal unique texts:")
    for i, text in enumerate(fuzzy_unique, 1):
        print(f"  {i}. {text}")

    # Statistics
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Original: {len(dataset)} texts")
    print(f"Exact duplicates removed: {len(dataset) - len(exact_unique)}")
    print(f"Fuzzy duplicates removed: {len(exact_unique) - len(fuzzy_unique)}")
    print(f"Final unique: {len(fuzzy_unique)} texts")
    print(f"Total removed: {len(dataset) - len(fuzzy_unique)} texts")
    print(f"Reduction: {(1 - len(fuzzy_unique)/len(dataset))*100:.1f}%")


if __name__ == "__main__":
    main()
