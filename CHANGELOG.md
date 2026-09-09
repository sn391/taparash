# Changelog

All notable changes to Taparash will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-09-09

### Added - Phase 3
- **Local NLI Model Support** (`engines/nli.py`)
  - `LocalNLI` class for natural language inference
  - Uses cross-encoder/nli-deberta-v3-base by default
  - 100% offline after initial model download

- **Contradiction Detection** (Gate 7)
  - `ContradictionDetector` class for detecting contradictory statements
  - Checks new text against stored context
  - Configurable confidence threshold
  - Integrated into main pipeline

- **Context Coherence Validation**
  - `CoherenceValidator` class for coherence checking
  - Validates text coherence with existing context
  - Supports entailment requirements

- **Performance Profiling Tools** (`profiler.py`)
  - `TaparashProfiler` class for detailed performance profiling
  - `benchmark_pipeline()` for benchmarking configurations
  - `compare_configurations()` for A/B testing
  - JSON export of profiling results
  - Per-gate timing and statistics

### Changed
- Updated `QualityConfig` with:
  - `check_contradictions` flag
  - `contradiction_threshold` parameter (0.0-1.0)
  - `nli_model_path` configuration
- Enhanced `TaparashFilter.reset()` to clear contradiction detector
- Updated statistics tracking to include contradiction rejections

### Documentation
- Added Phase 3 examples to README.md
- Added contradiction detection usage examples
- Added performance profiling examples
- Updated architecture diagram with Gate 7
- Marked Phase 3 as completed

## [0.2.0] - 2026-09-09

### Added - Phase 2
- **Dead Letter Queue** (`dlq.py`)
  - SQLite-based audit logging for rejected chunks
  - Query and analysis capabilities
  - JSON export for compliance reporting
  - Automatic cleanup of old records
  - Statistics by rejection reason

- **Local Embeddings** (`engines/embeddings.py`)
  - `LocalEmbedder` class using sentence-transformers
  - All-MiniLM-L6-v2 model (22MB, 384 dimensions)
  - Batch embedding support
  - 100% offline after initial download

- **Semantic Deduplication** (Gate 6)
  - `SemanticDeduplicator` class for vector-based deduplication
  - Cosine similarity matching
  - Configurable similarity threshold (default: 0.90)
  - Detects paraphrases and semantic near-duplicates

- **Batch Processing Optimization**
  - Configurable batch size for large datasets
  - Chunked processing for memory efficiency
  - Optimized for millions of chunks

- **Parallel Processing Support**
  - Multi-threaded execution with ThreadPoolExecutor
  - Thread-safe deduplication with locks
  - Configurable worker count
  - Stateless gates run in parallel

### Changed
- Updated `QualityConfig` with:
  - `enable_dlq` and `dlq_path` parameters
  - `enable_semantic_dedup` and `semantic_threshold`
  - `batch_size` and `parallel_workers` parameters
  - `embeddings_model_path` configuration
- Refactored `process_batch()` to support parallel processing
- Split gate processing into stateless and stateful operations
- Added thread locks for concurrent safety

### Documentation
- Added Phase 2 examples to README.md
- Added semantic deduplication usage examples
- Added large-scale parallel processing examples
- Updated performance benchmarks

## [0.1.0] - Initial Release

### Added - Phase 1
- **Core Filtering Pipeline** (`pipeline.py`)
  - `TaparashFilter` main class
  - Sequential gate-based processing
  - Statistics tracking
  - Batch processing support

- **Configuration System** (`config.py`)
  - `QualityConfig` with full validation
  - `FilterResult` and `BatchResult` classes
  - Configurable thresholds for all gates

- **Length Validation** (Gate 1)
  - Min/max length checks
  - Configurable thresholds

- **PII Masking** (Gate 2) (`core/pii.py`)
  - Email address detection
  - Phone number detection (US & international)
  - Credit card detection with Luhn validation
  - Social Security Number detection
  - IP address detection (optional)
  - Configurable replacement token

- **Entropy Filtering** (Gate 3) (`core/entropy.py`)
  - Shannon entropy calculation
  - Gibberish detection
  - Configurable threshold

- **Exact Deduplication** (Gate 4) (`core/deduplication.py`)
  - SHA-256 based hashing
  - O(1) lookup performance
  - ~64 bytes per unique hash

- **Fuzzy Deduplication** (Gate 5) (`core/deduplication.py`)
  - MinHash LSH algorithm
  - Configurable similarity threshold
  - Word or character-based shingles
  - Configurable permutations

### Features
- **100% Offline Operation** - No external API calls
- **Zero-LLM Overhead** - Deterministic algorithms only
- **Privacy-First** - GDPR and EU AI Act compliant
- **Air-Gapped Ready** - Suitable for regulated industries
- **High Performance** - <10ms latency per chunk (core features)

### Documentation
- Comprehensive README.md with examples
- API reference documentation
- Configuration guide
- Performance benchmarks
- Installation instructions

---

## Version History Summary

- **v0.3.0** (2026-09-09): Phase 3 - NLI, Contradiction Detection, Profiling
- **v0.2.0** (2026-09-09): Phase 2 - DLQ, Semantic Dedup, Parallel Processing
- **v0.1.0** (Initial): Phase 1 - Core Filtering, PII, Deduplication

[0.3.0]: https://github.com/sn391/taparash/releases/tag/v0.3.0
[0.2.0]: https://github.com/sn391/taparash/releases/tag/v0.2.0
[0.1.0]: https://github.com/sn391/taparash/releases/tag/v0.1.0
