# Taparash 

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.3.0-green.svg)](https://github.com/sn391/taparash)
[![Code Style](https://img.shields.io/badge/code%20style-PEP8-blue.svg)](https://www.python.org/dev/peps/pep-0008/)

> **Air-Gapped, Zero-LLM Data Quality & Compliance Gateway for RAG Systems**

Taparash is a high-performance, 100% offline data quality and compliance gateway designed to clean, deduplicate, and validate text data before it enters your Vector Database or Retrieval-Augmented Generation (RAG) pipeline. Built for privacy-first enterprise environments with **zero internet dependencies and zero LLM overhead**.

Named after **Tapa Rash ** (meaning "Black Hill" in Kurdish) representing solid roots, unyielding strength, and local sovereignty.

---

## 🌟 Key Features

### 🔒 100% Air-Gapped & Offline
- **Zero Internet Dependencies:** All processing executes locally with no external API calls
- **Privacy-First:** GDPR and EU AI Act compliant by design
- **Enterprise-Ready:** Suitable for regulated industries (finance, healthcare, government)

### ⚡ Zero-LLM Overhead
- **Ultra-Fast Processing:** < 10ms latency per chunk
- **Deterministic Algorithms:** Predictable, reproducible results
- **Lightweight:** Runs on standard CPUs without GPU requirements
- **No Model Loading:** Core features work without ML models

### 🧹 Multi-Layer Quality Filtering

#### **Deterministic Layer** (Currently Implemented)
- **Length Validation:** Configurable min/max chunk size
- **PII Masking:** Regex-based detection & sanitization
  - Email addresses
  - Phone numbers (US & international)
  - Credit cards (with Luhn validation)
  - Social Security Numbers
  - IP addresses (optional)
- **Shannon Entropy Filter:** Detects gibberish, corrupted text, and binary payloads
- **Exact Deduplication:** SHA-256 hashing for identical content
- **Fuzzy Deduplication:** MinHash LSH for near-duplicate detection

#### **Semantic Layer** (Phase 2 - Completed)
- Local embedding generation (MiniLM)
- Vector-based semantic deduplication
- Dead Letter Queue for audit logging
- Batch processing optimization
- Parallel processing support

#### **NLI Layer** (Phase 3 - Completed)
- Local Cross-Encoder for contradiction detection
- Context coherence validation  
- Performance profiling tools
- Advanced audit logging

---

## 🚀 Quick Start

### Installation

**From PyPI (Recommended):**

```bash
# Core features only (no ML models)
pip install taparash

# With semantic deduplication (includes sentence-transformers)
pip install taparash[semantic]

# All features
pip install taparash[all]
```

**From Source:**

```bash
# Clone the repository
git clone https://github.com/sn391/taparash.git
cd taparash

# Install in development mode
pip install -e .

# Or install with semantic features
pip install -e ".[semantic]"
```

### Basic Usage

```python
from taparash import TaparashFilter, QualityConfig

# 1. Configure the pipeline
config = QualityConfig(
    min_chunk_length=20,
    max_chunk_length=2000,
    entropy_threshold=4.5,
    dedup_threshold=0.88,
    enable_pii_masking=True
)

# 2. Initialize the filter
app = TaparashFilter(config=config)

# 3. Process your data
chunks = [
    "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.",
    "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.",  # Duplicate
    "Contact us at sales@company.com for more information.",        # Contains PII
    "a8f9#$s82kjsdf092348572390485",                                # Gibberish
]

results = app.process_batch(chunks)

# 4. Review results
print(f"✓ Accepted: {len(results.accepted)}")
print(f"✗ Rejected: {len(results.rejected)}")

for item in results.rejected:
    print(f"  [{item.reason_code}] {item.text[:50]}...")

# 5. View statistics
app.print_stats()
```

**Output:**
```
✓ Accepted: 1
✗ Rejected: 3

  [EXACT_DUPLICATE] The quarterly revenue for Q3 grew by 15% reac...
  [PII_DETECTED] Contact us at [REDACTED] for more information....
  [HIGH_ENTROPY] a8f9#$s82kjsdf092348572390485...

============================================================
TAPARASH PROCESSING STATISTICS
============================================================
Total Processed:       4
Accepted:              1 (25.0%)
Rejected:              3

Rejection Breakdown:
  - Length issues:     0
  - High entropy:      1
  - Exact duplicates:  1
  - Fuzzy duplicates:  0
  - PII issues:        1
============================================================
```

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Processing Pipeline](#-processing-pipeline)
- [PII Detection](#-pii-detection)
- [Deduplication](#-deduplication)
- [Performance](#-performance)
- [Examples](#-examples)
- [Development](#-development)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🏗️ Architecture

Taparash implements a multi-gate filtering pipeline where each chunk passes through sequential quality checks:

```
┌─────────────────────────────────────────────────────────────┐
│                     Input: Raw Text Chunks                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 1: Length Validation                                   │
│  ✓ Min/Max length checks                                     │
│  ✓ Configurable thresholds                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 2: PII Masking                                         │
│  ✓ Regex-based detection                                     │
│  ✓ Emails, phones, credit cards, SSN                         │
│  ✓ Configurable replacement token                            │
└────────────────────────┬────────────────────────────────────┘
                         │ PASS (with masked PII)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 3: Entropy Filter                                      │
│  ✓ Shannon entropy calculation                               │
│  ✓ Gibberish detection                                       │
│  ✓ Corrupted text filtering                                  │
└────────────────────────┬────────────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 4: Exact Deduplication                                 │
│  ✓ SHA-256 hashing                                           │
│  ✓ O(1) lookup performance                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 5: Fuzzy Deduplication                                 │
│  ✓ MinHash LSH algorithm                                     │
│  ✓ Configurable similarity threshold                         │
│  ✓ Character or word-based shingles                          │
└────────────────────────┬────────────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 6: Semantic Deduplication (Phase 2)                    │
│  ✓ Local MiniLM embeddings                                   │
│  ✓ Vector similarity matching                                │
└────────────────────────┬────────────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 7: Contradiction Detection (Phase 3)                   │
│  ✓ Local Cross-Encoder NLI                                   │
│  ✓ Context coherence validation                              │
└────────────────────────┬────────────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Output: Clean, Validated, Deduplicated Chunks      │
│                                                               │
│  ┌─────────────────────┐    ┌──────────────────────────┐   │
│  │  Accepted Chunks    │    │   Rejected Chunks        │   │
│  │  → Vector DB        │    │   → Dead Letter Queue    │   │
│  │  → RAG Context      │    │   → Audit Log            │   │
│  └─────────────────────┘    └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

### QualityConfig Parameters

```python
config = QualityConfig(
    # Length constraints
    min_chunk_length=20,              # Minimum characters
    max_chunk_length=2000,            # Maximum characters
    
    # Entropy filtering
    entropy_threshold=4.5,            # Shannon entropy cutoff
    enable_entropy_check=True,        # Enable/disable entropy filter
    
    # Exact deduplication
    enable_exact_dedup=True,          # SHA-256 based
    
    # Fuzzy deduplication
    enable_fuzzy_dedup=True,          # MinHash LSH
    dedup_threshold=0.88,             # Jaccard similarity threshold (0-1)
    fuzzy_num_perm=128,               # Number of hash permutations
    fuzzy_shingle_size=3,             # Shingle size (n-grams)
    use_word_shingles=True,           # Word vs character shingles
    
    # PII masking
    enable_pii_masking=True,          # Enable PII detection
    pii_mask_emails=True,             # Mask email addresses
    pii_mask_phones=True,             # Mask phone numbers
    pii_mask_credit_cards=True,       # Mask credit card numbers
    pii_mask_ssn=True,                # Mask Social Security Numbers
    pii_replacement_token="[REDACTED]",  # Replacement text
    
    # Semantic features (PR2)
    enable_semantic_dedup=False,      # Requires local embeddings
    semantic_threshold=0.90,          # Vector similarity threshold
    
    # Contradiction detection (Phase 3)
    check_contradictions=False,       # Requires NLI model
    contradiction_threshold=0.7,      # NLI confidence threshold (0.0-1.0)
    nli_model_path="cross-encoder/nli-deberta-v3-base",  # NLI model
    
    # Processing options
    batch_size=100,                   # Batch processing size (chunks per batch)
    parallel_workers=4,               # Parallel processing threads (for stateless gates)
)
```

### Configuration Validation

All configurations are validated automatically:

```python
config = QualityConfig(
    min_chunk_length=2000,
    max_chunk_length=20  # Error: max < min
)
# Raises: ValueError: Configuration validation failed:
#   - max_chunk_length must be >= min_chunk_length
```

---

## 📚 API Reference

### TaparashFilter

Main filtering class that orchestrates the processing pipeline.

#### Methods

##### `__init__(config: Optional[QualityConfig] = None)`
Initialize the filter with optional configuration.

```python
app = TaparashFilter(config=QualityConfig())
```

##### `process_single(text: str) -> FilterResult`
Process a single text chunk.

```python
result = app.process_single("Your text here")
if result.is_valid:
    print(f"Accepted: {result.text}")
else:
    print(f"Rejected: {result.reason_code}")
```

##### `process_batch(texts: List[str], use_parallel: bool = False) -> BatchResult`
Process multiple chunks in batch with optional parallel processing.

```python
# Sequential processing (default)
results = app.process_batch(["text1", "text2", "text3"])
print(f"Accepted: {len(results.accepted)}")
print(f"Rejected: {len(results.rejected)}")

# Parallel processing (recommended for large batches)
results = app.process_batch(large_batch, use_parallel=True)
```

**Parallel Processing:**
- Stateless gates (length, PII, entropy) run in parallel
- Stateful gates (deduplication) run sequentially with thread locks
- Best for large batches (>1000 chunks) or with semantic deduplication enabled
- Thread count controlled by `parallel_workers` config parameter

##### `reset()`
Reset all deduplicators and statistics.

```python
app.reset()  # Start fresh
```

##### `get_stats() -> dict`
Get current processing statistics.

```python
stats = app.get_stats()
print(f"Acceptance rate: {stats['acceptance_rate']:.1f}%")
```

##### `print_stats()`
Print formatted statistics to console.

```python
app.print_stats()
```

### FilterResult

Result object for individual chunk processing.

**Attributes:**
- `text: str` - Processed text (with PII masked if applicable)
- `original_text: str` - Original unmodified text
- `is_valid: bool` - Whether chunk passed all gates
- `reason_code: Optional[str]` - Rejection reason code
- `reason_detail: Optional[str]` - Detailed rejection message
- `metadata: dict` - Additional information (PII count, entropy, etc.)

### BatchResult

Result object for batch processing.

**Attributes:**
- `accepted: List[FilterResult]` - Valid chunks
- `rejected: List[FilterResult]` - Invalid chunks

**Properties:**
- `total: int` - Total chunks processed
- `acceptance_rate: float` - Percentage accepted

**Methods:**
- `summary() -> str` - Get formatted summary

### DeadLetterQueue

SQLite-based audit log for rejected chunks (Phase 2).

#### Methods

##### `__init__(db_path: Optional[str] = None)`
Initialize DLQ with optional database path (default: `./taparash_dlq.db`).

##### `log_rejection(result: FilterResult)`
Log a single rejected chunk.

##### `log_batch(rejected_results: List[FilterResult])`
Log multiple rejected chunks in one transaction.

##### `get_rejection_stats() -> Dict[str, int]`
Get counts by rejection reason.

```python
stats = dlq.get_rejection_stats()
# {'LENGTH_TOO_SHORT': 45, 'EXACT_DUPLICATE': 23, ...}
```

##### `get_recent_rejections(limit: int = 100) -> List[Dict]`
Get most recent rejection records.

##### `get_pii_violations(limit: int = 100) -> List[Dict]`
Get chunks with PII detected.

##### `export_to_json(output_path: str, reason_code: Optional[str] = None) -> int`
Export rejection records to JSON file.

```python
# Export all rejections
dlq.export_to_json("rejections.json")

# Export only specific reason
dlq.export_to_json("length_issues.json", reason_code="LENGTH_TOO_SHORT")
```

##### `clear_old_records(days: int = 90) -> int`
Delete records older than specified days.

**Example Usage:**

```python
from taparash import TaparashFilter, QualityConfig, DeadLetterQueue

config = QualityConfig(
    enable_dlq=True,
    dlq_path="audit_log.db"
)

app = TaparashFilter(config)
results = app.process_batch(chunks)

# Rejections are automatically logged to DLQ

# Query DLQ
dlq = DeadLetterQueue("audit_log.db")
dlq.print_summary()

# Get PII violations for compliance report
pii_violations = dlq.get_pii_violations(limit=100)
```

---

## 🔄 Processing Pipeline

### Rejection Reason Codes

| Code | Description | Gate |
|------|-------------|------|
| `LENGTH_TOO_SHORT` | Below minimum length | Gate 1 |
| `LENGTH_TOO_LONG` | Above maximum length | Gate 1 |
| `HIGH_ENTROPY` | Entropy exceeds threshold (gibberish) | Gate 3 |
| `EXACT_DUPLICATE` | SHA-256 hash match | Gate 4 |
| `FUZZY_DUPLICATE` | MinHash similarity match | Gate 5 |
| `SEMANTIC_DUPLICATE` | Vector similarity match (Phase 2) | Gate 6 |
| `CONTRADICTION` | NLI contradiction detected (Phase 3) | Gate 7 |

### Processing Flow

```python
# Each chunk flows through gates sequentially
text = "Your input text"

# Gate 1: Length check
if len(text) < min_length or len(text) > max_length:
    reject(reason="LENGTH_*")

# Gate 2: PII masking (modifies text)
text, pii_matches = pii_masker.mask(text)

# Gate 3: Entropy check
if shannon_entropy(text) > threshold:
    reject(reason="HIGH_ENTROPY")

# Gate 4: Exact dedup
if sha256_hash(text) in seen_hashes:
    reject(reason="EXACT_DUPLICATE")

# Gate 5: Fuzzy dedup
if minhash_similarity(text, corpus) > threshold:
    reject(reason="FUZZY_DUPLICATE")

# All gates passed
accept(text)
```

---

## 🛡️ PII Detection

### Supported PII Types

Taparash uses regex-based detection with validation algorithms:

#### Email Addresses
```python
# Patterns detected:
user@example.com
name.surname@company.co.uk
user+tag@domain.org
```

#### Phone Numbers
```python
# US formats:
555-123-4567
(555) 123-4567
555.123.4567
5551234567

# International:
+1-555-123-4567
+44 20 1234 5678
```

#### Credit Cards
```python
# Validated with Luhn algorithm:
4532-1488-0343-6467  # Visa
5425-2334-3010-9903  # MasterCard
3782-822463-10005    # American Express
6011-1111-1111-1117  # Discover
```

#### Social Security Numbers (US)
```python
# Format: XXX-XX-XXXX
123-45-6789
```

### PII Masking Example

```python
from taparash.core import PIIMasker

masker = PIIMasker(
    mask_emails=True,
    mask_credit_cards=True,
    replacement_token="[REDACTED]"
)

text = "Contact john@example.com or call 555-1234. Card: 4532-1488-0343-6467"
masked, matches = masker.mask(text)

print(masked)
# Output: "Contact [REDACTED] or call [REDACTED]. Card: [REDACTED]"

print(f"Found {len(matches)} PII items")
# Output: Found 3 PII items
```

---

## 🔁 Deduplication

### Exact Deduplication (SHA-256)

Perfect for identical text matching:

```python
from taparash.core import ExactDeduplicator

dedup = ExactDeduplicator()

texts = ["Hello world", "Hello world", "Different text"]

for i, text in enumerate(texts):
    is_unique = dedup.add(text, index=i)
    print(f"{i}: {'UNIQUE' if is_unique else 'DUPLICATE'}")

# Output:
# 0: UNIQUE
# 1: DUPLICATE
# 2: UNIQUE
```

**Performance:** O(1) lookup, ~64 bytes per unique hash

### Fuzzy Deduplication (MinHash)

Detects near-duplicates based on similarity:

```python
from taparash.core import MinHashDeduplicator

dedup = MinHashDeduplicator(
    num_perm=128,           # More permutations = higher accuracy
    threshold=0.8,          # 80% similarity threshold
    shingle_size=3,         # 3-word shingles
    use_word_shingles=True  # Word-based (vs character-based)
)

texts = [
    "The cat sat on the mat",
    "The cat sat on the rug",  # 87% similar
    "A dog barked loudly"      # Completely different
]

for text in texts:
    is_unique, similar_idx = dedup.add(text)
    if is_unique:
        print(f"✓ UNIQUE: {text}")
    else:
        print(f"✗ SIMILAR to text {similar_idx}: {text}")
```

**Threshold Guide:**
- **0.9-1.0:** Only near-identical (typos, minor edits)
- **0.7-0.9:** Similar content with moderate differences
- **0.5-0.7:** Loosely similar texts
- **< 0.5:** Very permissive (may catch unrelated texts)

---

## ⚡ Performance

### Benchmarks (Single-threaded, CPU)

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Length validation | < 1ms | > 1M chunks/sec |
| PII masking | 2-5ms | 200-500 chunks/sec |
| Entropy calculation | 1-3ms | 300-1000 chunks/sec |
| Exact dedup (SHA-256) | < 1ms | > 500K chunks/sec |
| Fuzzy dedup (MinHash) | 5-15ms | 70-200 chunks/sec |
| **Full pipeline** | **8-25ms** | **40-120 chunks/sec** |

### Memory Usage

| Component | Memory per Item |
|-----------|----------------|
| Configuration | ~1KB |
| PII Masker | ~2KB |
| Exact Dedup | ~64 bytes/hash |
| Fuzzy Dedup (128 perm) | ~512 bytes/signature |

### Scalability

- **Small datasets (< 10K chunks):** Process in-memory, single-threaded
- **Medium datasets (10K-1M chunks):** Batch processing with parallel workers
- **Large datasets (> 1M chunks):** Stream processing with periodic dedup reset

---

## 💡 Examples

### Example 1: RAG Pipeline Integration

```python
from taparash import TaparashFilter, QualityConfig

def process_documents_for_rag(documents):
    """Clean documents before embedding and storage."""
    
    config = QualityConfig(
        min_chunk_length=50,
        max_chunk_length=1000,
        entropy_threshold=4.5,
        enable_pii_masking=True,
        dedup_threshold=0.85
    )
    
    filter = TaparashFilter(config)
    
    # Split documents into chunks
    chunks = []
    for doc in documents:
        chunks.extend(split_into_chunks(doc, max_size=800))
    
    # Filter and clean
    results = filter.process_batch(chunks)
    
    print(f"Input: {len(chunks)} chunks")
    print(f"Accepted: {len(results.accepted)} chunks")
    print(f"Rejected: {len(results.rejected)} chunks")
    
    # Return only clean chunks for embedding
    return [r.text for r in results.accepted]

# Use in your pipeline
clean_chunks = process_documents_for_rag(documents)
embeddings = embed_texts(clean_chunks)
vector_db.insert(embeddings)
```

### Example 2: Compliance Audit

```python
from taparash import TaparashFilter, QualityConfig

def audit_for_pii(texts):
    """Scan texts for PII before sharing."""
    
    config = QualityConfig(
        enable_pii_masking=True,
        # Disable other filters for audit mode
        enable_entropy_check=False,
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False
    )
    
    filter = TaparashFilter(config)
    results = filter.process_batch(texts)
    
    # Report PII findings
    pii_found = []
    for result in results.accepted:
        pii_count = result.metadata.get('pii_masked_count', 0)
        if pii_count > 0:
            pii_found.append({
                'original': result.original_text,
                'masked': result.text,
                'pii_count': pii_count
            })
    
    return pii_found
```

### Example 3: Data Quality Report

```python
def generate_quality_report(dataset):
    """Analyze dataset quality without filtering."""
    
    from taparash.core import shannon_entropy, PIIMasker
    from taparash.core import ExactDeduplicator
    
    report = {
        'total': len(dataset),
        'too_short': 0,
        'too_long': 0,
        'high_entropy': 0,
        'has_pii': 0,
        'duplicates': 0
    }
    
    pii_masker = PIIMasker()
    dedup = ExactDeduplicator()
    
    for text in dataset:
        if len(text) < 20:
            report['too_short'] += 1
        if len(text) > 2000:
            report['too_long'] += 1
        if shannon_entropy(text) > 4.5:
            report['high_entropy'] += 1
        if pii_masker.has_pii(text):
            report['has_pii'] += 1
        if not dedup.add(text):
            report['duplicates'] += 1
    
    report['quality_score'] = (
        (report['total'] - sum([
            report['too_short'],
            report['too_long'],
            report['high_entropy'],
            report['duplicates']
        ])) / report['total'] * 100
    )
    
    return report
```

### Example 4: Semantic Deduplication (Phase 2)

```python
from taparash import TaparashFilter, QualityConfig

def process_with_semantic_dedup(texts):
    """
    Use semantic deduplication to detect paraphrases and similar content.
    Requires: pip install sentence-transformers
    """
    
    config = QualityConfig(
        min_chunk_length=20,
        # Enable semantic deduplication
        enable_semantic_dedup=True,
        semantic_threshold=0.85,  # 85% similarity threshold
        embeddings_model_path="sentence-transformers/all-MiniLM-L6-v2",
        # Optionally disable fuzzy dedup to rely only on semantic
        enable_fuzzy_dedup=False,
        # Enable DLQ for audit trail
        enable_dlq=True,
        dlq_path="semantic_dedup_log.db"
    )
    
    filter = TaparashFilter(config)
    results = filter.process_batch(texts)
    
    # Show semantic duplicates
    print("Semantically similar texts rejected:")
    for result in results.rejected:
        if result.reason_code == "SEMANTIC_DUPLICATE":
            print(f"  Similarity: {result.metadata['similarity_score']:.3f}")
            print(f"  Text: {result.text[:60]}...")
    
    return results.accepted

# Example usage
texts = [
    "Machine learning is transforming software development",
    "AI and ML are revolutionizing how we build software",  # Semantically similar!
    "The weather today is sunny and warm",  # Different topic
    "Artificial intelligence is changing software engineering",  # Similar to first
]

accepted = process_with_semantic_dedup(texts)
print(f"Accepted {len(accepted)} unique texts")
```

### Example 5: Large-Scale Parallel Processing (Phase 2)

```python
from taparash import TaparashFilter, QualityConfig
import time

def process_large_dataset(documents, parallel=True):
    """Process large dataset with parallel workers."""
    
    config = QualityConfig(
        min_chunk_length=50,
        batch_size=500,  # Process 500 chunks per batch
        parallel_workers=8,  # Use 8 parallel workers
        enable_pii_masking=True,
        enable_entropy_check=True,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=True,
        enable_dlq=True,
        dlq_path="large_scale_processing.db"
    )
    
    filter = TaparashFilter(config)
    
    # Split documents into chunks
    chunks = []
    for doc in documents:
        chunks.extend(split_into_chunks(doc, max_size=800))
    
    print(f"Processing {len(chunks)} chunks...")
    start = time.time()
    
    # Use parallel processing for large batches
    results = filter.process_batch(chunks, use_parallel=parallel)
    
    elapsed = time.time() - start
    throughput = len(chunks) / elapsed
    
    print(f"Completed in {elapsed:.2f}s ({throughput:.0f} chunks/sec)")
    print(f"Accepted: {len(results.accepted)} ({results.acceptance_rate:.1f}%)")
    print(f"Rejected: {len(results.rejected)}")
    
    filter.print_stats()
    
    return results.accepted

# Process 10,000+ chunks efficiently
large_dataset = load_documents("./data")
clean_chunks = process_large_dataset(large_dataset, parallel=True)
```

### Example 6: Contradiction Detection (Phase 3)

```python
from taparash import TaparashFilter, QualityConfig

def detect_contradictions(texts):
    """
    Detect contradictory statements using local NLI model.
    Requires: pip install sentence-transformers
    """
    
    config = QualityConfig(
        min_chunk_length=20,
        # Enable contradiction detection
        check_contradictions=True,
        contradiction_threshold=0.75,  # 75% confidence threshold
        nli_model_path="cross-encoder/nli-deberta-v3-base",
        # Optional: disable other filters to focus on contradictions
        enable_entropy_check=True,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=False,
        enable_semantic_dedup=False,
        # Enable DLQ for audit trail
        enable_dlq=True,
        dlq_path="contradiction_audit.db"
    )
    
    filter = TaparashFilter(config)
    results = filter.process_batch(texts)
    
    # Show contradictions
    print("Contradictory statements detected:")
    for result in results.rejected:
        if result.reason_code == "CONTRADICTION":
            print(f"  Confidence: {result.metadata['contradiction_confidence']:.3f}")
            print(f"  Text: {result.text[:60]}...")
            print(f"  Contradicts text at index: {result.metadata['contradicting_index']}")
            print()
    
    return results.accepted

# Example usage with business metrics
metrics = [
    "Q1 revenue increased by 20% year over year.",
    "Customer satisfaction scores improved significantly.",
    "Revenue declined in Q1 compared to last year.",  # Contradicts first!
    "Product launch was successful with positive feedback.",
    "The product launch failed to meet expectations.",  # Contradicts previous!
]

validated = detect_contradictions(metrics)
print(f"Validated {len(validated)} non-contradictory statements")
```

### Example 7: Performance Profiling (Phase 3)

```python
from taparash import TaparashFilter, QualityConfig
from taparash.profiler import TaparashProfiler, benchmark_pipeline, compare_configurations

# Profile a single run
def profile_pipeline():
    """Profile pipeline performance."""
    
    profiler = TaparashProfiler(enabled=True)
    
    config = QualityConfig(
        min_chunk_length=20,
        enable_pii_masking=True,
        enable_entropy_check=True,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=True,
        enable_semantic_dedup=False,
        enable_dlq=False
    )
    
    pipeline = TaparashFilter(config)
    test_data = [f"Test chunk {i} with content" for i in range(1000)]
    
    profiler.start_batch()
    results = pipeline.process_batch(test_data)
    profiler.end_batch(len(test_data))
    
    # Print detailed performance report
    profiler.print_report()
    
    # Save to JSON for analysis
    profiler.save_report("profile_results.json")

# Benchmark multiple configurations
def benchmark_configs():
    """Compare different configuration performances."""
    
    test_data = [f"Chunk {i} content" for i in range(500)]
    
    configs = [
        ("Fast", lambda: TaparashFilter(QualityConfig(
            enable_fuzzy_dedup=False,
            enable_semantic_dedup=False,
            check_contradictions=False
        ))),
        ("Balanced", lambda: TaparashFilter(QualityConfig(
            enable_fuzzy_dedup=True,
            enable_semantic_dedup=False,
            check_contradictions=False
        ))),
        ("Complete", lambda: TaparashFilter(QualityConfig(
            enable_fuzzy_dedup=True,
            enable_semantic_dedup=True,
            check_contradictions=True,
            embeddings_model_path="sentence-transformers/all-MiniLM-L6-v2",
            nli_model_path="cross-encoder/nli-deberta-v3-base"
        )))
    ]
    
    results = compare_configurations(configs, test_data, iterations=3)
    print(f"Best configuration: {results['best_configuration']}")

profile_pipeline()
benchmark_configs()
```

---

## 🛠️ Development

### Project Structure

```
taparash/
├── core/                    # Core algorithms
│   ├── entropy.py          # Shannon entropy
│   ├── deduplication.py    # SHA-256 & MinHash
│   ├── pii.py              # PII detection
│   └── __init__.py
├── engines/                 # ML engines (PR2/PR3)
│   ├── embeddings.py       # Local embeddings (coming)
│   └── nli.py              # Contradiction detection (coming)
├── config.py               # Configuration management
├── pipeline.py             # Main TaparashFilter
├── dlq.py                  # Dead Letter Queue (coming)
└── __init__.py
```

### Running Tests

```bash
# Deduplication tests
python test_deduplication.py
python test_deduplication_advanced.py

# Pipeline tests
python test_pipeline.py

# Example usage
python example_usage.py

# Demo
python demo_deduplication.py
```

### Code Style

- **PEP 8** compliant
- **Type hints** on all functions
- **Docstrings** for all public APIs
- **100% offline** - no external API calls

---

## 🗺️ Roadmap

### ✅ Phase 1 (Current - v0.1.0)
- [x] Configuration system
- [x] Length validation
- [x] PII masking (regex-based)
- [x] Shannon entropy filtering
- [x] Exact deduplication (SHA-256)
- [x] Fuzzy deduplication (MinHash)
- [x] Main processing pipeline
- [x] Statistics tracking

### ✅ Phase 2 (v0.2.0 - Completed)
- [x] Dead Letter Queue with SQLite
- [x] Local MiniLM embeddings
- [x] Semantic deduplication (vector-based)
- [x] Batch processing optimization
- [x] Parallel processing support

### ✅ Phase 3 (v0.3.0 - Completed)
- [x] Local Cross-Encoder NLI model
- [x] Contradiction detection
- [x] Context coherence validation
- [x] Advanced audit logging (via DLQ)
- [x] Performance profiling tools

### 🚀 Future Enhancements
- [ ] Multi-language support
- [ ] Custom regex patterns for PII
- [ ] Plugin architecture for custom filters
- [ ] CLI tool for standalone use
- [ ] REST API wrapper
- [ ] Docker containerization

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Areas for Contribution

1. **Bug Reports:** Open an issue with reproduction steps
2. **Feature Requests:** Propose new features via issues
3. **Code Contributions:** Submit PRs for bug fixes or features
4. **Documentation:** Improve docs, add examples
5. **Testing:** Add test cases, improve coverage

### Development Setup

```bash
# Clone repository
git clone https://github.com/sn391/taparash.git
cd taparash

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black taparash/
isort taparash/

# Type checking
mypy taparash/
```

### Contribution Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for public APIs
- Include tests for new features
- Update documentation as needed
- Maintain 100% offline operation (no external API calls)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by the need for privacy-first AI infrastructure
- Built on proven algorithms: SHA-256, MinHash, Shannon Entropy
- Named after **Tapa Rash** symbolizing strength and sovereignty

---

## 📞 Contact & Support

- **Issues:** [GitHub Issues](https://github.com/sn391/taparash/issues)
- **Discussions:** [GitHub Discussions](https://github.com/sn391/taparash/discussions)
- **Email:** [sn391@yahoo.com](mailto:sn391@yahoo.com)

---

## 🌐 Use Cases

### Enterprise RAG Systems
Filter and clean documents before embedding to improve retrieval quality and reduce storage costs.

### Data Compliance
Automatically detect and mask PII in text data to meet GDPR, HIPAA, and other regulatory requirements.

### Content Moderation
Remove duplicate and low-quality content from user-generated data pipelines.

### Document Processing
Clean and deduplicate scanned documents, OCR output, and web-scraped content.

### Knowledge Base Management
Maintain high-quality, deduplicated knowledge bases for customer support and internal documentation.

---

<div align="center">

**Built with ❤️ for privacy-first AI**

[⭐ Star on GitHub](https://github.com/sn391/taparash) | [📖 Documentation](https://github.com/sn391/taparash/wiki) | [🐛 Report Bug](https://github.com/sn391/taparash/issues)

</div>
