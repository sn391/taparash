# Taparash

[![PyPI version](https://badge.fury.io/py/taparash.svg)](https://pypi.org/project/taparash/)
[![Python Version](https://img.shields.io/pypi/pyversions/taparash.svg)](https://pypi.org/project/taparash/)
[![Tests](https://github.com/sn391/taparash/actions/workflows/tests.yml/badge.svg)](https://github.com/sn391/taparash/actions/workflows/tests.yml)
[![Build](https://github.com/sn391/taparash/actions/workflows/build.yml/badge.svg)](https://github.com/sn391/taparash/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Air-Gapped, Zero-LLM Data Quality & Compliance Gateway for RAG Systems**

100% offline data quality filtering with PII masking, deduplication, and semantic analysis. No internet. No LLMs. No GPU required.

---

## Installation

```bash
pip install taparash                   # core only
pip install taparash[semantic]         # + semantic dedup & contradiction detection
pip install taparash[connectors]       # + PDF / HTML document loaders
pip install taparash[distributed]      # + Ray-based distributed processing
pip install taparash[all]              # everything
```

---

## Quick Start

```python
from taparash import TaparashFilter, QualityConfig

config = QualityConfig(
    min_chunk_length=20,
    max_chunk_length=2000,
    entropy_threshold=4.5,
    dedup_threshold=0.88,
    enable_pii_masking=True,
)

f = TaparashFilter(config)
results = f.process_batch([
    "Q3 revenue grew 15% to 4.2M EUR.",
    "Q3 revenue grew 15% to 4.2M EUR.",   # duplicate
    "Contact sales@company.com for info.", # PII
    "a8f9#$s82kjsdf09234857",              # gibberish
])

print(results.summary())
# Processed: 4 | Accepted: 1 | Rejected: 3
```

---

## Pipeline Gates

Each chunk passes through gates in order. The first failure stops processing.

| Gate | Check | Rejection Code |
|------|-------|----------------|
| 1 | Length (min / max) | `LENGTH_TOO_SHORT` / `LENGTH_TOO_LONG` |
| 2 | PII masking | — (text is masked, not rejected) |
| 3 | Shannon entropy (gibberish) | `HIGH_ENTROPY` |
| 4 | Exact dedup (SHA-256) | `EXACT_DUPLICATE` |
| 5 | Fuzzy dedup (MinHash LSH) | `FUZZY_DUPLICATE` |
| 6 | Semantic dedup (MiniLM) | `SEMANTIC_DUPLICATE` |
| 7 | Contradiction detection (NLI) | `CONTRADICTION` |

Gates 6 and 7 require `pip install taparash[semantic]`.

---

## Key Features

### Core (always available)
- **PII Masking** — regex-based; emails, phones, credit cards (Luhn-validated), SSNs, IPs
- **Extensible PII** — plug in any custom detector via `PIIDetector` protocol
- **Exact + Fuzzy Dedup** — SHA-256 hash and MinHash LSH
- **Entropy Filter** — rejects gibberish, binary payloads, corrupted OCR
- **Dead Letter Queue** — SQLite audit log of every rejected chunk with provenance

### Semantic (requires `sentence-transformers`)
- Local MiniLM embeddings for vector-based dedup
- Local Cross-Encoder NLI for contradiction detection

### Document Connectors (requires `taparash[connectors]`)
- `load_pdf(path)` → `List[DocumentChunk]` (heading detection, table metadata)
- `load_html(source)` → `List[DocumentChunk]` (trafilatura + BeautifulSoup fallback)
- `DocumentChunk` carries `source_file`, `page_num`, `heading`, `is_table` metadata through the pipeline

### Observability
```python
from taparash import QualityConfig, TaparashFilter

config = QualityConfig(
    enable_dlq=False,
    metrics_callback=lambda m: print(m.as_dict()),
)
f = TaparashFilter(config)
f.process_batch(chunks)
# → {"total": 100, "accepted": 83, "pii_hits": 12, "wall_time_ms": 41.3, ...}
```

### Distributed Processing (requires `ray`)
```python
from taparash.backends import RayBackend
from taparash import TaparashFilter, QualityConfig

backend = RayBackend(num_cpus=8, shard_size=200)
f = TaparashFilter(QualityConfig(enable_dlq=False), backend=backend)
results = f.process_batch(large_chunk_list)
# Stateless gates fan out across Ray workers; dedup runs locally on coordinator
```

---

## Configuration Reference

```python
QualityConfig(
    # Length
    min_chunk_length=20,
    max_chunk_length=2000,

    # Entropy
    entropy_threshold=4.2,
    enable_entropy_check=True,

    # Deduplication
    enable_exact_dedup=True,
    enable_fuzzy_dedup=True,
    dedup_threshold=0.88,          # Jaccard similarity (0–1)
    fuzzy_num_perm=128,
    use_word_shingles=True,

    # PII
    enable_pii_masking=True,
    pii_mask_emails=True,
    pii_mask_phones=True,
    pii_mask_credit_cards=True,
    pii_mask_ssn=True,
    pii_replacement_token="[REDACTED]",

    # Semantic (requires taparash[semantic])
    enable_semantic_dedup=False,
    semantic_threshold=0.90,
    check_contradictions=False,
    contradiction_threshold=0.7,

    # Processing
    batch_size=100,
    parallel_workers=4,
    distributed_backend=None,      # "ray" when using RayBackend

    # Audit
    enable_dlq=True,
    dlq_path=None,                 # default: ./taparash_dlq.db

    # Observability
    metrics_callback=None,         # Callable[[PipelineMetrics], None]
)
```

---

## Extensible PII Detection

```python
from taparash import PIIMasker, PIIMatch

class SpacyNERDetector:
    def __init__(self, nlp):
        self.nlp = nlp

    def detect(self, text: str) -> list[PIIMatch]:
        doc = self.nlp(text)
        return [
            PIIMatch(ent.label_.lower(), ent.start_char, ent.end_char, ent.text)
            for ent in doc.ents if ent.label_ in {"PERSON", "ORG"}
        ]

masker = PIIMasker()
masker.register_detector(SpacyNERDetector(spacy.load("en_core_web_sm")))
```

---

## Benchmarks

Run the harness on your own hardware to get reproducible, hardware-normalised numbers:

```bash
python benchmarks/run_benchmark.py          # full suite (~3 min)
python benchmarks/run_benchmark.py --quick  # smoke test (~25 s)
```

Results are written to `benchmarks/results/benchmark_<date>_<host>.json` and `.md`.

**What is measured:**

| Suite | Description |
|-------|-------------|
| Per-gate latency | Median / P95 / P99 µs per chunk for each isolated gate |
| End-to-end throughput | Chunks/s and **MB/s per CPU core** at batch sizes 100 → 10k |
| Parallel scaling | Throughput vs. worker count (1 → N cores) |
| Memory | Peak RSS delta and MB per million tokens |

**Reference numbers — stateless gates only (`--no-fuzzy`)**

> Hardware: Intel Core i7-8550U · 8 logical / 4 physical cores · 16.9 GB RAM · Windows 11 · Python 3.12.9

| Batch size | Chunks/s | MB/s | MB/s per core |
|-----------|---------|------|---------------|
| 100 | 8,936 | 2.83 | **0.354** |
| 500 | 8,860 | 2.84 | **0.355** |

Per-gate latency (median µs/chunk):

| Gate | Median µs | P95 µs |
|------|-----------|--------|
| Length validation | 3.4 | 3.4 |
| Exact dedup (SHA-256) | 5.9 | 6.6 |
| Entropy check | 62.0 | 63.6 |
| PII masking | 148.1 | 154.9 |
| Fuzzy dedup (MinHash-128) | 15,035 | 15,245 |
| **Full pipeline (no fuzzy)** | **132.9** | **149.3** |

> MinHash is intentionally excluded from the throughput headline — at 128 permutations it dominates (~15 ms/chunk) and is not comparable to tools that skip probabilistic dedup. Run `python benchmarks/run_benchmark.py` (without `--no-fuzzy`) to measure the complete pipeline on your hardware.

**Comparison with other tools**

These tools solve adjacent but distinct sub-problems. A fair comparison must:
1. Run each tool's own benchmark on the **same hardware**.
2. Report CPU model, core count, RAM, and OS.
3. State what each tool actually does (scope differs).

| Tool | Scope | How to benchmark |
|------|-------|-----------------|
| **taparash** | Post-parse quality filtering (dedup, PII, entropy) | `python benchmarks/run_benchmark.py --no-fuzzy` |
| NeMo Curator | Full dataset curation incl. GPU-accelerated dedup | NeMo Curator's own benchmark scripts |
| Unstructured.io | Document parsing (PDF/HTML → text) | Unstructured's benchmark CLI |

---

## Development

```bash
git clone https://github.com/sn391/taparash.git
cd taparash
pip install -e ".[all,dev]"
pytest tests/
```

---

## Roadmap

| Version | Status | Highlights |
|---------|--------|------------|
| v0.1 | ✅ | Length, PII, entropy, exact + fuzzy dedup |
| v0.2 | ✅ | Semantic dedup, DLQ, parallel processing |
| v0.3 | ✅ | NLI contradiction detection, profiling, document connectors |
| v0.4 | ✅ | Observability, extensible PII, distributed (Ray) backend |
| v0.5 | 🔜 | Multi-language PII, CLI tool, REST API wrapper |

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

[GitHub](https://github.com/sn391/taparash) · [Issues](https://github.com/sn391/taparash/issues) · [PyPI](https://pypi.org/project/taparash/)

</div>
