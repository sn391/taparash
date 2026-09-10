"""
Taparash - Zero-LLM Data Quality & Compliance Gateway for RAG Systems.

100% offline, air-gapped data quality filtering with PII masking,
deduplication, semantic analysis, and contradiction detection.
"""

__version__ = "0.3.0"

# Core imports - relative imports within package
from .core import (
    shannon_entropy,
    is_gibberish,
    sha256_hash,
    ExactDeduplicator,
    MinHashDeduplicator,
    create_shingles,
    create_word_shingles,
    deduplicate_exact,
    deduplicate_fuzzy,
    PIIMasker,
    PIIMatch,
    mask_pii,
)

# Main components - relative imports
from .config import QualityConfig, FilterResult, BatchResult, DocumentChunk
from .pipeline import TaparashFilter
from .dlq import DeadLetterQueue
from .profiler import TaparashProfiler, benchmark_pipeline, compare_configurations, profile_comparison

# Optional connectors (require taparash[connectors])
__all_optional__ = []

try:
    from .connectors import load_html, load_pdf
    __all_optional__.extend(["load_html", "load_pdf"])
except ImportError:
    pass

# Optional Phase 2 & 3 components (require sentence-transformers)

try:
    from .engines import LocalEmbedder, SemanticDeduplicator
    __all_optional__.extend(["LocalEmbedder", "SemanticDeduplicator"])
except ImportError:
    pass

try:
    from .engines.nli import LocalNLI, ContradictionDetector, CoherenceValidator
    __all_optional__.extend(["LocalNLI", "ContradictionDetector", "CoherenceValidator"])
except ImportError:
    pass

__all__ = [
    # Version
    "__version__",
    # Core entropy
    "shannon_entropy",
    "is_gibberish",
    # Core deduplication
    "sha256_hash",
    "ExactDeduplicator",
    "MinHashDeduplicator",
    "create_shingles",
    "create_word_shingles",
    "deduplicate_exact",
    "deduplicate_fuzzy",
    # Core PII
    "PIIMasker",
    "PIIMatch",
    "mask_pii",
    # Config & Results
    "QualityConfig",
    "FilterResult",
    "BatchResult",
    "DocumentChunk",
    # Main Pipeline
    "TaparashFilter",
    # Phase 2: DLQ & Profiling
    "DeadLetterQueue",
    "TaparashProfiler",
    "benchmark_pipeline",
    "compare_configurations",
    "profile_comparison",
] + __all_optional__
