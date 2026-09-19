"""Core utilities for taparash."""

from .entropy import shannon_entropy, is_gibberish
from .deduplication import (
    sha256_hash,
    ExactDeduplicator,
    MinHashDeduplicator,
    create_shingles,
    create_word_shingles,
    deduplicate_exact,
    deduplicate_fuzzy,
)
from .pii import PIIMasker, PIIMatch, mask_pii, PIIDetector
from .quality import HeuristicQualityFilter, QualityCheckResult
from .langid import LanguageFilter

__all__ = [
    "shannon_entropy",
    "is_gibberish",
    "sha256_hash",
    "ExactDeduplicator",
    "MinHashDeduplicator",
    "create_shingles",
    "create_word_shingles",
    "deduplicate_exact",
    "deduplicate_fuzzy",
    "PIIMasker",
    "PIIMatch",
    "mask_pii",
    "PIIDetector",
    "HeuristicQualityFilter",
    "QualityCheckResult",
    "LanguageFilter",
]
