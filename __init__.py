"""Taparash - Zero-LLM Data Quality & Compliance Gateway."""

from taparash.core import (
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
from taparash.config import QualityConfig, FilterResult, BatchResult
from taparash.pipeline import TaparashFilter
from taparash.dlq import DeadLetterQueue

# Optional semantic components
try:
    from taparash.engines import LocalEmbedder
    __all_engines__ = ["LocalEmbedder"]
except ImportError:
    __all_engines__ = []

__version__ = "0.1.0"

__all__ = [
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
    # Config
    "QualityConfig",
    "FilterResult",
    "BatchResult",
    # Pipeline
    "TaparashFilter",
    # DLQ
    "DeadLetterQueue",
] + __all_engines__
