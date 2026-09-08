# Taparash (تپه رش) ⛰️

> **Air-Gapped, Zero-LLM Data Quality & Compliance Gateway for RAG Systems**

[![PyPI version](https://badge.fury.io/py/taparash.svg)](https://badge.fury.io/py/taparash)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Taparash** is a high-performance, 100% offline Data Quality & Compliance Gateway designed to clean, deduplicate, and validate data before it enters your Vector Database or Retrieval-Augmented Generation (RAG) pipeline.

Built for privacy-first enterprise environments (GDPR & EU AI Act compliant), Taparash executes deterministic filtering and ultra-fast local ML models directly within your internal network with **zero internet dependencies and zero LLM overhead**.

---

## 🌟 Key Features

* **🔒 100% Air-Gapped & Offline (Zero Internet):** All embeddings, NLI classification, and entropy calculations execute locally. No external API calls to OpenAI, Hugging Face, or third-party clouds.
* **⚡ Zero-LLM Overhead (<10ms Latency):** Uses deterministic algorithms and lightweight local encoders (`MiniLM`, `DeBERTa-Small`) instead of heavy Generative LLMs. Runs on standard CPUs without GPU requirements.
* **🧹 Smart Deduplication & Anomaly Removal:**
  * **Exact Deduplication:** High-speed SHA-256 and MurmurHash filtering.
  * **Fuzzy Deduplication:** MinHash / LSH for syntactic similarity.
  * **Semantic Deduplication:** Vector clustering using local embeddings.
* **🔬 Shannon Entropy Filter:** Detects corrupted text, gibberish, binary payloads, and unstructured noise automatically.
* **⚖️ Semantic Contradiction Engine (NLI):** Flags contradictory context chunks using local Cross-Encoders before they reach your LLM context window.
* **🛡️ Compliance & PII Masking:** Built-in regex engines to sanitize sensitive data (emails, credit cards, government IDs) for strict GDPR compliance.
* **📥 Dead Letter Queue (DLQ):** Route rejected chunks to a local SQL/vector audit log with detailed reason codes for compliance auditing.

---

## 🚀 Why "Taparash"?

Named after **Tepe Rash (تپه رش)** — meaning "Black Hill" in Kurdish — representing solid roots, unyielding strength, and local data sovereignty. Taparash acts as an impenetrable local shield for your enterprise AI infrastructure.

---

## 🏗️ Architecture & Processing Pipeline

```mermaid
flowchart TD
    A[Raw Data Chunks / Ingestion] --> B[Taparash Gateway]
    
    subgraph Taparash [Taparash Processing Core - 100% Local]
        B --> C{Deterministic Layer}
        C -->|Check 1| C1[Length & PII Masking]
        C -->|Check 2| C2[Shannon Entropy Check]
        C -->|Check 3| C3[SHA-256 & MinHash Exact/Fuzzy Deduplication]
        
        C1 & C2 & C3 -->|Passed| D{Semantic & NLI Layer}
        D -->|Step 1| D1[Local Embeddings - all-MiniLM-L6-v2]
        D -->|Step 2| D2[Local Cross-Encoder - Contradiction Score]
    end
    
    D1 & D2 -->|Valid Chunk| E[Clean Vector DB / RAG Context Window]
    C1 & C2 & C3 & D2 -->|Rejected Chunk| F[Dead Letter Queue DLQ + Audit Log]






Quick start :

from taparash import TaparashFilter, QualityConfig

# 1. Initialize Configuration (100% Offline)
config = QualityConfig(
    min_chunk_length=20,
    max_chunk_length=2000,
    entropy_threshold=4.2,  # Shannon Entropy cutoff for gibberish
    dedup_threshold=0.88,   # Semantic duplicate threshold
    check_contradictions=True,
    enable_pii_masking=True
)

# 2. Instantiate Taparash Engine
app = TaparashFilter(config=config)

# 3. Sample Data Chunks
chunks = [
    "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.",
    "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.", # Duplicate
    "Q3 revenue dropped by 50% causing major losses.",             # Contradiction
    "a8f9#$s82kjsdf092348572390485723904857239048572390485",       # Gibberish/Entropy fail
]

# 4. Filter Pipeline Execution
results = app.process_batch(chunks)

print(f"Clean Chunks Accepted: {len(results.accepted)}")
print(f"Rejected Chunks: {len(results.rejected)}")

# Inspect Rejections & DLQ Reasons
for item in results.rejected:
    print(f"Text: '{item.text}' | Reason: {item.reason_code}")


taparash/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── taparash/
│       ├── __init__.py
│       ├── config.py
│       ├── core/
│       │   ├── entropy.py       # Shannon entropy engine
│       │   ├── deduplication.py # Hashes, MinHash, LSH
│       │   └── pii.py           # Sanitization & regex masking
│       ├── engines/
│       │   ├── embeddings.py    # Local MiniLM vectorizer
│       │   └── nli.py           # Local Cross-Encoder contradiction engine
│       ├── pipeline.py          # Main processing orchestration
│       └── dlq.py               # Dead Letter Queue storage
└── tests/
    ├── test_entropy.py
    ├── test_deduplication.py
    └── test_pipeline.py