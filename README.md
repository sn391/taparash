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
pip install taparash[langid]           # + language identification (fastText)
pip install taparash[anonymizer]       # + Faker for realistic PII replacement
pip install taparash[distributed]      # + Ray-based distributed processing
pip install taparash[langchain]        # + LangChain BaseDocumentTransformer
pip install taparash[llamaindex]       # + LlamaIndex BaseNodePostprocessor
pip install taparash[api]              # + FastAPI REST server
pip install taparash[metrics]          # + Prometheus metrics exporter
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
| 4 | Heuristic quality (Gopher/C4 rules) | `HIGH_LINE_LENGTH_RATIO` / `HIGH_SYMBOL_DENSITY` / `HIGH_WORD_REPETITION` |
| 5 | Language identification | `LANGUAGE_NOT_ALLOWED` |
| 6 | Exact dedup (SHA-256) | `EXACT_DUPLICATE` |
| 7 | Fuzzy dedup (MinHash LSH) | `FUZZY_DUPLICATE` |
| 8 | Semantic dedup (MiniLM) | `SEMANTIC_DUPLICATE` |
| 9 | Contradiction detection (NLI) | `CONTRADICTION` |

**Gates 4–5 (Heuristic quality & Language ID):** Optional, disabled by default. No extra dependencies for heuristic quality; language identification requires `pip install taparash[langid]`.

**Gates 8–9 (Semantic):** Require `pip install taparash[semantic]`.

---

## Key Features

### Core (always available)
- **PII Masking** — regex-based; emails, phones, credit cards (Luhn-validated), SSNs, IPs, dates, times
- **PII Anonymization Strategies** — `"redact"` (default), `"hash"` (SHA-256 prefix), `"replace"` (realistic Faker data), or `"tag"` (label type). Per-entity overrides: `strategies={"email": "hash", "phone": "replace"}`
- **European PII** (opt-in) — IBAN (ISO 13616), EU VAT (27 member states + UK), local phone formats (UK/FR/DE)
- **Extensible PII** — plug in any custom detector via `PIIDetector` protocol
- **Exact + Fuzzy Dedup** — SHA-256 hash and MinHash LSH
- **Heuristic Quality Filter** — Gopher/C4 rules: line-length ratio, symbol density, word repetition
- **Language Identification** — offline fastText via `langdetect` (optional)
- **Entropy Filter** — rejects gibberish, binary payloads, corrupted OCR
- **Dead Letter Queue** — SQLite audit log of every rejected chunk with provenance

### Semantic (requires `sentence-transformers`)
- Local MiniLM embeddings for vector-based dedup
- Local Cross-Encoder NLI for contradiction detection

### Document Connectors (requires `taparash[connectors]`)
- `load_pdf(path)` → `List[DocumentChunk]` (heading detection, table metadata)
- `load_html(source)` → `List[DocumentChunk]` (trafilatura + BeautifulSoup fallback)
- `DocumentChunk` carries `source_file`, `page_num`, `heading`, `is_table` metadata through the pipeline

### Async API

Both `process_single` and `process_batch` have async equivalents — safe to use in FastAPI handlers, async LangChain chains, or any other `async`/`await` context:

```python
import asyncio
from taparash import TaparashFilter, QualityConfig

f = TaparashFilter(QualityConfig())

# Single chunk
result = await f.aprocess_single(text)

# Batch
batch = await f.aprocess_batch(texts)

# Fan out multiple batches concurrently
results = await asyncio.gather(
    f.aprocess_batch(batch_a),
    f.aprocess_batch(batch_b),
)
```

Dedup state is shared and thread-safe — concurrent calls accumulate into the same dedup index correctly.

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
    pii_mask_dates=False,                          # ISO dates, DD/MM/YYYY, times
    pii_replacement_token="[REDACTED]",
    pii_anonymization_strategy="redact",           # "redact" | "hash" | "replace" | "tag"
    pii_strategies={},                             # per-entity overrides, e.g. {"email": "hash"}
    # European PII (opt-in)
    pii_mask_iban=False,        # IBAN with ISO 13616 mod-97 checksum validation
    pii_mask_eu_vat=False,      # EU VAT numbers for all 27 member states + UK
    pii_mask_eu_phone=False,    # UK/FR/DE local phone formats (no +CC prefix)

    # Heuristic quality (Gopher/C4 rules; opt-in)
    enable_heuristic_quality=False,
    heuristic_max_line_length=1000,
    heuristic_max_line_length_ratio=0.3,           # max % of lines exceeding max_line_length
    heuristic_max_symbol_density=0.1,              # max % of non-alphanumeric characters
    heuristic_max_word_repetition_ratio=0.5,       # max % of duplicate word tokens

    # Language identification (requires taparash[langid]; opt-in)
    enable_language_filter=False,
    allowed_languages=["en"],                      # ISO 639-1 codes

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

## PII Anonymization Strategies

Four strategies are available for replacing detected PII:

| Strategy | Example Output | Deterministic | Notes |
|----------|---|---|---|
| `"redact"` | `[REDACTED]` | ✓ | Default; simple masking. |
| `"hash"` | `[SHA:3a7f9c2e]` | ✓ | SHA-256 prefix (8 hex chars). Good for audit trails / pseudonymization. |
| `"replace"` | `user123@mail.com` | ✗ | Realistic fake data via Faker. Requires `pip install taparash[anonymizer]`. Falls back to hash if Faker unavailable. |
| `"tag"` | `[EMAIL]` | ✓ | Replace with PII type label. Useful for downstream analysis. |

**Global strategy:**
```python
from taparash import PIIMasker

masker = PIIMasker(anonymization_strategy="hash")
masked, _ = masker.mask("Contact admin@company.com")
# → "Contact [SHA:7f8a9e2c]"
```

**Per-entity overrides:**
```python
from taparash import TaparashFilter, QualityConfig

config = QualityConfig(
    pii_anonymization_strategy="redact",
    pii_strategies={"email": "hash", "phone": "replace", "ssn": "tag"},
)
# Emails → hash, phones → Faker replacement, SSNs → [SSN], everything else → [REDACTED]
```

---

## Heuristic Quality Rules

Three Gopher/C4–style heuristic checks (all optional, disabled by default):

```python
from taparash import TaparashFilter, QualityConfig

config = QualityConfig(
    enable_heuristic_quality=True,
    heuristic_max_line_length=1000,            # chars above which a line is "too long"
    heuristic_max_line_length_ratio=0.3,       # reject if >30% of lines are too long
    heuristic_max_symbol_density=0.1,          # reject if >10% non-alphanumeric chars
    heuristic_max_word_repetition_ratio=0.5,   # reject if >50% words are duplicates
)

f = TaparashFilter(config)
result = f.process_single("click click click buy now buy now")
# → rejected with reason_code="HIGH_WORD_REPETITION"
```

---

## Language Identification

Filter text by detected language (optional; requires `pip install taparash[langid]`):

```python
from taparash import TaparashFilter, QualityConfig

config = QualityConfig(
    enable_language_filter=True,
    allowed_languages=["en", "de", "fr"],
)

f = TaparashFilter(config)
result = f.process_single("Bonjour le monde")
# → accepted (French is in allowed list)

result = f.process_single("你好世界")
# → rejected with reason_code="LANGUAGE_NOT_ALLOWED"
```

The language filter gracefully degrades if `langdetect` is not installed — chunks pass through without language checks. This ensures the pipeline never breaks on a missing optional dependency.

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

## Config Files

Config can be stored in `.yaml`/`.yml` or `.toml` — no Python required.

**`pipeline.toml`**
```toml
min_chunk_length = 20
max_chunk_length = 2000
entropy_threshold = 4.5
enable_fuzzy_dedup = false
pii_mask_iban = true
pii_mask_eu_vat = true
enable_dlq = false
```

**`pipeline.yaml`**
```yaml
min_chunk_length: 20
entropy_threshold: 4.5
enable_pii_masking: true
pii_mask_iban: true
enable_dlq: false
```

```python
from taparash import load_config, save_config

config = load_config("pipeline.yaml")   # or .toml
f = TaparashFilter(config)

save_config(config, "pipeline.toml")    # serialize back out
```

TOML works without extra dependencies on Python 3.11+. YAML requires `pip install taparash[yaml]`.

---

## CLI

```bash
# Load settings from a config file (CLI flags override file values)
taparash filter corpus.jsonl clean.jsonl --config pipeline.toml --stats

# Filter a JSONL dataset
taparash filter corpus.jsonl clean.jsonl --stats

# Pipe from stdin
cat raw.jsonl | taparash filter - --no-fuzzy --stats > clean.jsonl

# Plain-text files (one chunk per line)
taparash filter raw.txt clean.txt --format txt --min-length 50

# PII masking only (no dedup / entropy / length)
taparash mask raw.jsonl masked.jsonl

# European PII opt-ins
taparash filter corpus.jsonl clean.jsonl --pii-iban --pii-eu-vat --pii-eu-phone

# Anonymization strategies
taparash filter corpus.jsonl clean.jsonl --pii-strategy hash --stats

# Heuristic quality + language filters
taparash filter corpus.jsonl clean.jsonl --enable-heuristic --allowed-languages en de fr

# Save rejected chunks for inspection
taparash filter corpus.jsonl clean.jsonl --rejected rejected.jsonl --no-dlq

# Version
taparash version
```

Key flags for `filter`:

| Flag | Effect |
|------|--------|
| `--no-pii` | Disable PII masking |
| `--no-dedup` | Disable all deduplication |
| `--no-fuzzy` | Disable MinHash dedup only |
| `--no-entropy` | Disable gibberish filter |
| `--pii-iban` | Enable IBAN detection |
| `--pii-eu-vat` | Enable EU VAT detection |
| `--pii-eu-phone` | Enable EU local phone detection |
| `--pii-dates` | Enable date/time PII detection (opt-in) |
| `--pii-strategy {redact,hash,replace,tag}` | Anonymization strategy (default: `redact`) |
| `--enable-heuristic` | Enable heuristic quality filter (Gopher/C4 rules) |
| `--allowed-languages LANG [LANG ...]` | Language whitelist, e.g. `en de fr` (requires `--enable-language-filter`) |
| `--enable-language-filter` | Enable language identification gate |
| `--rejected FILE` | Write rejected chunks (with reason) to FILE |
| `--stats` | Print summary counts to stderr |
| `--text-field FIELD` | JSON field containing the text (default: `text`) |

---

## LangChain Integration

```bash
pip install taparash[langchain]
```

```python
from taparash.integrations.langchain import TaparashDocumentTransformer
from taparash import QualityConfig

transformer = TaparashDocumentTransformer(
    config=QualityConfig(enable_pii_masking=True, enable_dlq=False),
    add_filter_metadata=True,   # injects taparash_accepted / taparash_pii_masked into metadata
)

# Works anywhere a BaseDocumentTransformer is accepted
clean_docs = transformer.transform_documents(raw_docs)
```

Drop it directly into an LCEL chain:

```python
chain = loader | transformer | embedder
```

`atransform_documents` is also available for async pipelines. Deduplication state accumulates across calls — create a new instance to reset between independent document sets.

---

## REST API

```bash
pip install taparash[api]

# Start server (default: http://127.0.0.1:8000)
taparash serve

# With config file and custom port
taparash serve --config pipeline.toml --host 0.0.0.0 --port 8080
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness probe |
| `/stats` | GET | Cumulative pipeline statistics |
| `/filter` | POST | Filter a batch — returns `accepted[]`, `rejected[]` with reason codes |
| `/filter/single` | POST | Filter one chunk |
| `/mask` | POST | PII masking only, no other gates |

```bash
# Filter a batch
curl -X POST http://localhost:8000/filter \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Valid content here.", "x", "Contact sales@acme.com."]}'

# Single chunk
curl -X POST http://localhost:8000/filter/single \
  -d '{"text": "Clean text."}'
```

Programmatic use:
```python
from taparash.server import create_app
from taparash import QualityConfig
import uvicorn

app = create_app(QualityConfig(enable_pii_masking=True, enable_dlq=False))
uvicorn.run(app, host="0.0.0.0", port=8000)
```

Interactive API docs available at `http://localhost:8000/docs` (Swagger UI).

---

## Prometheus Metrics

```bash
pip install taparash[metrics]
```

When `prometheus-client` is installed, `GET /metrics` is automatically available on the REST server in standard Prometheus text format:

```bash
taparash serve --config pipeline.toml
curl http://localhost:8000/metrics
```

Exported metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `taparash_chunks_processed_total` | Counter | Total chunks seen |
| `taparash_chunks_accepted_total` | Counter | Chunks that passed all gates |
| `taparash_chunks_rejected_total{reason}` | Counter | Rejected chunks, labelled by reason (`length`, `entropy`, `exact_duplicate`, …) |
| `taparash_acceptance_rate` | Gauge | Fraction accepted (0.0–1.0) |
| `taparash_pipeline_info` | Info | Static labels: `version`, `python` |

Standalone use in any ASGI/WSGI app:

```python
from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from taparash.metrics_exporter import TaparashCollector

registry = CollectorRegistry()
TaparashCollector(pipeline, registry=registry)

# In your /metrics route:
return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
```

---

## LlamaIndex Integration

```bash
pip install taparash[llamaindex]
```

```python
from taparash.integrations.llamaindex import TaparashNodePostprocessor
from taparash import QualityConfig

postprocessor = TaparashNodePostprocessor(
    config=QualityConfig(enable_pii_masking=True, enable_dlq=False),
    add_filter_metadata=True,   # injects taparash_accepted / taparash_pii_masked into metadata
)

# Attach to a RetrieverQueryEngine
query_engine = index.as_query_engine(
    node_postprocessors=[postprocessor]
)

# Or call directly
filtered_nodes = postprocessor.postprocess_nodes(raw_nodes)
```

Node scores and metadata are preserved. Original nodes are never mutated — the postprocessor copies each node before applying PII masking. Deduplication state accumulates across calls; create a new instance to reset between independent document sets.

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
| v0.5 | ✅ | Multi-language PII (IBAN/VAT/EU phone), CLI tool, LangChain adapter |
| v0.6 | ✅ | LlamaIndex adapter, async API (`aprocess_batch`), REST API, YAML/TOML config, CLI |
| v0.7 | ✅ | Prometheus metrics (`/metrics` endpoint + `TaparashCollector`) |
| v0.8 | 🔜 | Streaming mode, custom gate plugins |

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

[GitHub](https://github.com/sn391/taparash) · [Issues](https://github.com/sn391/taparash/issues) · [PyPI](https://pypi.org/project/taparash/)

</div>
