# Deduplication Module

Comprehensive text deduplication using exact (SHA256) and fuzzy (MinHash) matching.

## Features

### 1. Exact Deduplication (SHA256)
- Uses SHA256 cryptographic hashing
- O(n) time complexity
- 100% accuracy for exact matches
- Case-sensitive
- Tracks duplicate groups

### 2. Fuzzy Deduplication (MinHash)
- Locality-Sensitive Hashing (LSH) via MinHash
- Detects near-duplicates based on Jaccard similarity
- Configurable similarity threshold
- Character or word-based shingles
- Deterministic with seed parameter

## Quick Start

```python
from taparash.core import deduplicate_exact, deduplicate_fuzzy

# Exact deduplication
texts = ["Hello", "Hello", "World"]
unique, indices = deduplicate_exact(texts)
# unique = ["Hello", "World"]
# indices = [0, 2]

# Fuzzy deduplication
texts = [
    "The cat sat on the mat",
    "The cat sat on the rug",  # Similar but different
    "A dog barked loudly"
]
unique, indices = deduplicate_fuzzy(texts, threshold=0.7)
```

## API Reference

### Exact Deduplication

#### `sha256_hash(text: str) -> str`
Calculate SHA256 hash of text.

#### `ExactDeduplicator`
Class-based exact deduplication with duplicate tracking.

```python
dedup = ExactDeduplicator()
is_new = dedup.add("Some text", index=0)
is_duplicate = dedup.is_duplicate("Some text")
duplicate_groups = dedup.get_duplicate_groups()
```

#### `deduplicate_exact(texts: List[str]) -> Tuple[List[str], List[int]]`
Batch exact deduplication.

### Fuzzy Deduplication

#### `create_shingles(text: str, k: int = 3) -> Set[str]`
Create character-based k-shingles.

#### `create_word_shingles(text: str, k: int = 3) -> Set[str]`
Create word-based k-shingles.

#### `MinHashDeduplicator`
Class-based fuzzy deduplication with configurable parameters.

```python
dedup = MinHashDeduplicator(
    num_perm=128,      # Number of hash functions (more = slower but more accurate)
    threshold=0.8,     # Similarity threshold (0-1)
    shingle_size=3,    # Shingle size
    use_word_shingles=False,  # Use word vs character shingles
    seed=42            # Random seed for deterministic hashing
)

is_unique, similar_idx = dedup.add(text)
similar_items = dedup.find_similar(text)
```

#### `deduplicate_fuzzy(texts, threshold=0.8, ...) -> Tuple[List[str], List[int]]`
Batch fuzzy deduplication.

## Configuration Guide

### Threshold Selection
- **0.9-1.0**: Only near-identical texts (typos, minor edits)
- **0.7-0.9**: Similar content with moderate differences
- **0.5-0.7**: Loosely similar texts
- **< 0.5**: Very permissive, may catch unrelated texts

### Shingle Size
- **Character shingles (k=3-5)**: Good for short texts, typos, encoding issues
- **Word shingles (k=2-4)**: Better for longer texts, semantic similarity

### Number of Permutations
- **64**: Fast but less accurate
- **128**: Good balance (default)
- **256+**: More accurate but slower

## Usage Examples

### Pipeline: Exact + Fuzzy
```python
# Remove exact duplicates first, then near-duplicates
exact_unique, _ = deduplicate_exact(texts)
fuzzy_unique, kept = deduplicate_fuzzy(
    exact_unique,
    threshold=0.7,
    use_word_shingles=True
)
```

### Finding Similar Documents
```python
dedup = MinHashDeduplicator(threshold=0.8)
for text in corpus:
    dedup.add(text)

# Find all similar to query
query = "Your query text"
similar = dedup.find_similar(query)
for idx, similarity in similar:
    print(f"Document {idx}: {similarity:.2%} similar")
```

### Duplicate Group Analysis
```python
dedup = ExactDeduplicator()
for i, text in enumerate(texts):
    dedup.add(text, index=i)

groups = dedup.get_duplicate_groups()
for group in groups:
    print(f"Duplicate group: {group}")
    # group = [0, 3, 7] means texts[0], texts[3], texts[7] are identical
```

## Performance Characteristics

### Exact Deduplication
- **Time**: O(n)
- **Space**: O(n)
- **Scalability**: Excellent (millions of documents)

### Fuzzy Deduplication
- **Time**: O(n × m × p) where m = num_perm, p = shingle count
- **Space**: O(n × m)
- **Scalability**: Good for thousands, slower for millions
  - Consider LSH banding for very large datasets

## Best Practices

1. **Always run exact dedup first** - It's faster and reduces fuzzy dedup workload
2. **Normalize text** - Lowercase, strip whitespace for better matching
3. **Tune parameters** - Test different thresholds on sample data
4. **Use word shingles** - Better for natural language text
5. **Increase num_perm** - For critical deduplication tasks (legal, compliance)

## Algorithm Details

### SHA256 Exact Matching
```
hash = SHA256(text)
if hash in seen_hashes:
    mark as duplicate
```

### MinHash Fuzzy Matching
```
1. Create shingles (n-grams) from text
2. Generate MinHash signature:
   For each hash function h:
       signature[h] = min(h(shingle) for all shingles)
3. Compare signatures:
   similarity = (matching_values / total_values)
4. If similarity >= threshold:
   mark as duplicate
```

## Limitations

1. **Word order matters** - "cat eats fish" vs "fish eats cat" may seem similar
2. **Short texts** - Harder to deduplicate accurately (< 20 words)
3. **Language mixing** - Works best with single-language texts
4. **Memory usage** - Stores all signatures in memory

## References

- [MinHash Wikipedia](https://en.wikipedia.org/wiki/MinHash)
- [Locality-Sensitive Hashing](https://en.wikipedia.org/wiki/Locality-sensitive_hashing)
- Broder, A. Z. (1997). "On the resemblance and containment of documents"
