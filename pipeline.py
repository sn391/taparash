"""Main processing pipeline for Taparash filtering."""

from typing import List, Optional
from taparash.config import QualityConfig, FilterResult, BatchResult
from taparash.core.entropy import shannon_entropy, is_gibberish
from taparash.core.deduplication import ExactDeduplicator, MinHashDeduplicator
from taparash.core.pii import PIIMasker


class TaparashFilter:
    """
    Main Taparash filtering pipeline.

    100% offline operation with zero external API calls.
    Processes text chunks through multiple quality gates:
    1. Length validation
    2. PII masking
    3. Entropy check (gibberish detection)
    4. Exact deduplication (SHA-256)
    5. Fuzzy deduplication (MinHash)
    6. Semantic deduplication (optional, requires local model)
    7. Contradiction detection (optional, requires NLI model)
    """

    def __init__(self, config: Optional[QualityConfig] = None):
        """
        Initialize Taparash filter with configuration.

        Args:
            config: Quality configuration (uses defaults if None)
        """
        self.config = config or QualityConfig()

        # Initialize components
        self._init_pii_masker()
        self._init_deduplicators()

        # Statistics
        self.stats = {
            "total_processed": 0,
            "rejected_length": 0,
            "rejected_entropy": 0,
            "rejected_exact_duplicate": 0,
            "rejected_fuzzy_duplicate": 0,
            "rejected_semantic_duplicate": 0,
            "rejected_contradiction": 0,
            "accepted": 0,
        }

    def _init_pii_masker(self):
        """Initialize PII masker component."""
        if self.config.enable_pii_masking:
            self.pii_masker = PIIMasker(
                mask_emails=self.config.pii_mask_emails,
                mask_phones=self.config.pii_mask_phones,
                mask_credit_cards=self.config.pii_mask_credit_cards,
                mask_ssn=self.config.pii_mask_ssn,
                replacement_token=self.config.pii_replacement_token
            )
        else:
            self.pii_masker = None

    def _init_deduplicators(self):
        """Initialize deduplication components."""
        if self.config.enable_exact_dedup:
            self.exact_dedup = ExactDeduplicator()
        else:
            self.exact_dedup = None

        if self.config.enable_fuzzy_dedup:
            self.fuzzy_dedup = MinHashDeduplicator(
                num_perm=self.config.fuzzy_num_perm,
                threshold=self.config.dedup_threshold,
                shingle_size=self.config.fuzzy_shingle_size,
                use_word_shingles=self.config.use_word_shingles
            )
        else:
            self.fuzzy_dedup = None

    def process_single(self, text: str) -> FilterResult:
        """
        Process a single text chunk through the filtering pipeline.

        Args:
            text: Input text string

        Returns:
            FilterResult with validation status and reason
        """
        original_text = text
        self.stats["total_processed"] += 1

        # Gate 1: Length validation
        text_length = len(text)
        if text_length < self.config.min_chunk_length:
            self.stats["rejected_length"] += 1
            return FilterResult(
                text=text,
                original_text=original_text,
                is_valid=False,
                reason_code="LENGTH_TOO_SHORT",
                reason_detail=f"Length {text_length} < minimum {self.config.min_chunk_length}",
                metadata={"length": text_length}
            )

        if text_length > self.config.max_chunk_length:
            self.stats["rejected_length"] += 1
            return FilterResult(
                text=text,
                original_text=original_text,
                is_valid=False,
                reason_code="LENGTH_TOO_LONG",
                reason_detail=f"Length {text_length} > maximum {self.config.max_chunk_length}",
                metadata={"length": text_length}
            )

        # Gate 2: PII masking
        pii_matches = []
        if self.pii_masker:
            text, pii_matches = self.pii_masker.mask(text)

        # Gate 3: Entropy check (gibberish detection)
        if self.config.enable_entropy_check:
            entropy = shannon_entropy(text)
            if is_gibberish(text, threshold=self.config.entropy_threshold):
                self.stats["rejected_entropy"] += 1
                return FilterResult(
                    text=text,
                    original_text=original_text,
                    is_valid=False,
                    reason_code="HIGH_ENTROPY",
                    reason_detail=f"Entropy {entropy:.2f} > threshold {self.config.entropy_threshold}",
                    metadata={
                        "entropy": entropy,
                        "pii_masked_count": len(pii_matches)
                    }
                )

        # Gate 4: Exact deduplication
        if self.exact_dedup:
            if not self.exact_dedup.add(text):
                self.stats["rejected_exact_duplicate"] += 1
                return FilterResult(
                    text=text,
                    original_text=original_text,
                    is_valid=False,
                    reason_code="EXACT_DUPLICATE",
                    reason_detail="Exact duplicate detected (SHA-256 match)",
                    metadata={"pii_masked_count": len(pii_matches)}
                )

        # Gate 5: Fuzzy deduplication
        if self.fuzzy_dedup:
            is_unique, similar_idx = self.fuzzy_dedup.add(text)
            if not is_unique:
                self.stats["rejected_fuzzy_duplicate"] += 1
                return FilterResult(
                    text=text,
                    original_text=original_text,
                    is_valid=False,
                    reason_code="FUZZY_DUPLICATE",
                    reason_detail=f"Near-duplicate detected (similar to index {similar_idx})",
                    metadata={
                        "similar_to_index": similar_idx,
                        "threshold": self.config.dedup_threshold,
                        "pii_masked_count": len(pii_matches)
                    }
                )

        # Gate 6: Semantic deduplication (not yet implemented)
        if self.config.enable_semantic_dedup:
            # TODO: Implement semantic deduplication using local embeddings
            pass

        # Gate 7: Contradiction detection (not yet implemented)
        if self.config.check_contradictions:
            # TODO: Implement contradiction detection using local NLI model
            pass

        # All gates passed
        self.stats["accepted"] += 1
        return FilterResult(
            text=text,
            original_text=original_text,
            is_valid=True,
            reason_code=None,
            reason_detail=None,
            metadata={
                "pii_masked_count": len(pii_matches),
                "entropy": shannon_entropy(text) if self.config.enable_entropy_check else None
            }
        )

    def process_batch(self, texts: List[str]) -> BatchResult:
        """
        Process a batch of text chunks.

        Args:
            texts: List of input text strings

        Returns:
            BatchResult with accepted and rejected chunks
        """
        result = BatchResult()

        for text in texts:
            filter_result = self.process_single(text)
            if filter_result.is_valid:
                result.accepted.append(filter_result)
            else:
                result.rejected.append(filter_result)

        return result

    def reset(self):
        """Reset all deduplicators and statistics."""
        if self.exact_dedup:
            self.exact_dedup.reset()

        if self.fuzzy_dedup:
            self.fuzzy_dedup.reset()

        self.stats = {
            "total_processed": 0,
            "rejected_length": 0,
            "rejected_entropy": 0,
            "rejected_exact_duplicate": 0,
            "rejected_fuzzy_duplicate": 0,
            "rejected_semantic_duplicate": 0,
            "rejected_contradiction": 0,
            "accepted": 0,
        }

    def get_stats(self) -> dict:
        """
        Get current processing statistics.

        Returns:
            Dictionary of statistics
        """
        stats = self.stats.copy()
        if stats["total_processed"] > 0:
            stats["acceptance_rate"] = (stats["accepted"] / stats["total_processed"]) * 100
        else:
            stats["acceptance_rate"] = 0.0
        return stats

    def print_stats(self):
        """Print current processing statistics."""
        stats = self.get_stats()
        print("=" * 60)
        print("TAPARASH PROCESSING STATISTICS")
        print("=" * 60)
        print(f"Total Processed:       {stats['total_processed']}")
        print(f"Accepted:              {stats['accepted']} ({stats['acceptance_rate']:.1f}%)")
        print(f"Rejected:              {stats['total_processed'] - stats['accepted']}")
        print()
        print("Rejection Breakdown:")
        print(f"  - Length issues:     {stats['rejected_length']}")
        print(f"  - High entropy:      {stats['rejected_entropy']}")
        print(f"  - Exact duplicates:  {stats['rejected_exact_duplicate']}")
        print(f"  - Fuzzy duplicates:  {stats['rejected_fuzzy_duplicate']}")
        print(f"  - Semantic dupes:    {stats['rejected_semantic_duplicate']}")
        print(f"  - Contradictions:    {stats['rejected_contradiction']}")
        print("=" * 60)
