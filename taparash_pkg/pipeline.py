"""Main processing pipeline for Taparash filtering."""

from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    # Try package import first (when installed via pip)
    from taparash.config import QualityConfig, FilterResult, BatchResult, DocumentChunk
    from taparash.core.entropy import shannon_entropy, is_gibberish
    from taparash.core.deduplication import ExactDeduplicator, MinHashDeduplicator
    from taparash.core.pii import PIIMasker
    from taparash.dlq import DeadLetterQueue
except ImportError:
    # Fall back to local imports (for development)
    from config import QualityConfig, FilterResult, BatchResult, DocumentChunk
    from core.entropy import shannon_entropy, is_gibberish
    from core.deduplication import ExactDeduplicator, MinHashDeduplicator
    from core.pii import PIIMasker
    from dlq import DeadLetterQueue

# Optional: Import semantic deduplication (requires sentence-transformers)
try:
    from taparash.engines.embeddings import LocalEmbedder, SemanticDeduplicator
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    LocalEmbedder = None
    SemanticDeduplicator = None

# Optional: Import NLI for contradiction detection (requires sentence-transformers)
try:
    from taparash.engines.nli import LocalNLI, ContradictionDetector
    NLI_AVAILABLE = True
except ImportError:
    NLI_AVAILABLE = False
    LocalNLI = None
    ContradictionDetector = None


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
        self._init_semantic_dedup()
        self._init_contradiction_detector()
        self._init_dlq()

        # Thread safety for parallel processing
        self._dedup_lock = Lock()
        self._stats_lock = Lock()

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

    def _init_semantic_dedup(self):
        """Initialize semantic deduplication component."""
        if self.config.enable_semantic_dedup:
            if not SEMANTIC_AVAILABLE:
                raise ImportError(
                    "sentence-transformers is required for semantic deduplication. "
                    "Install with: pip install sentence-transformers"
                )

            # Initialize embedder and semantic deduplicator
            embedder = LocalEmbedder(
                model_name=self.config.embeddings_model_path,
                cache_dir=None  # Use default cache
            )
            self.semantic_dedup = SemanticDeduplicator(
                embedder=embedder,
                threshold=self.config.semantic_threshold,
                store_texts=False  # Don't store texts for memory efficiency
            )
        else:
            self.semantic_dedup = None

    def _init_contradiction_detector(self):
        """Initialize contradiction detector component."""
        if self.config.check_contradictions:
            if not NLI_AVAILABLE:
                raise ImportError(
                    "sentence-transformers is required for contradiction detection. "
                    "Install with: pip install sentence-transformers"
                )

            # Initialize NLI model and contradiction detector
            nli_model = LocalNLI(
                model_name=self.config.nli_model_path,
                cache_dir=None  # Use default cache
            )
            self.contradiction_detector = ContradictionDetector(
                nli_model=nli_model,
                threshold=self.config.contradiction_threshold,
                store_texts=True,
                max_context_size=100  # Keep last 100 chunks for context
            )
        else:
            self.contradiction_detector = None

    def _init_dlq(self):
        """Initialize Dead Letter Queue for audit logging."""
        if self.config.enable_dlq:
            self.dlq = DeadLetterQueue(db_path=self.config.dlq_path)
        else:
            self.dlq = None

    @staticmethod
    def _normalize_input(item: "Union[str, DocumentChunk]") -> "Tuple[str, dict]":
        """Return (text, source_metadata) from a str or DocumentChunk."""
        if isinstance(item, str):
            return item, {}
        return item.text, item.metadata

    def process_single(self, text: "Union[str, DocumentChunk]") -> FilterResult:
        """
        Process a single text chunk through the filtering pipeline.

        Args:
            text: Input text string or DocumentChunk (from a connector)

        Returns:
            FilterResult with validation status and reason
        """
        raw_text, source_metadata = self._normalize_input(text)
        original_text = raw_text

        with self._stats_lock:
            self.stats["total_processed"] += 1

        # Process stateless gates
        processed_text, pii_matches, rejection = self._process_stateless_gates(raw_text, original_text)

        if rejection:
            rejection.source_metadata = source_metadata
            return rejection

        # Process stateful gates
        result = self._process_stateful_gates(processed_text, original_text, pii_matches)
        result.source_metadata = source_metadata
        return result

    def _process_stateless_gates(self, text: str, original_text: str) -> Optional[Tuple[str, List, Optional[FilterResult]]]:
        """
        Process stateless gates (length, PII, entropy) that can run in parallel.

        Args:
            text: Input text
            original_text: Original unmodified text

        Returns:
            Tuple of (processed_text, pii_matches, rejection_result)
            If rejection_result is not None, the chunk was rejected
        """
        # Gate 1: Length validation
        text_length = len(text)
        if text_length < self.config.min_chunk_length:
            with self._stats_lock:
                self.stats["rejected_length"] += 1
            return None, [], FilterResult(
                text=text,
                original_text=original_text,
                is_valid=False,
                reason_code="LENGTH_TOO_SHORT",
                reason_detail=f"Length {text_length} < minimum {self.config.min_chunk_length}",
                metadata={"length": text_length}
            )

        if text_length > self.config.max_chunk_length:
            with self._stats_lock:
                self.stats["rejected_length"] += 1
            return None, [], FilterResult(
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

        # Gate 3: Entropy check
        if self.config.enable_entropy_check:
            entropy = shannon_entropy(text)
            if is_gibberish(text, threshold=self.config.entropy_threshold):
                with self._stats_lock:
                    self.stats["rejected_entropy"] += 1
                return None, [], FilterResult(
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

        # Passed all stateless gates
        return text, pii_matches, None

    def _process_stateful_gates(self, text: str, original_text: str, pii_matches: List) -> FilterResult:
        """
        Process stateful gates (deduplication) that must run sequentially.

        Args:
            text: Processed text
            original_text: Original text
            pii_matches: List of PII matches from masking

        Returns:
            FilterResult
        """
        # Gate 4: Exact deduplication
        if self.exact_dedup:
            with self._dedup_lock:
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
            with self._dedup_lock:
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

        # Gate 6: Semantic deduplication
        if self.semantic_dedup:
            with self._dedup_lock:
                is_unique, similar_idx, similarity = self.semantic_dedup.add(text)
                if not is_unique:
                    self.stats["rejected_semantic_duplicate"] += 1
                    return FilterResult(
                        text=text,
                        original_text=original_text,
                        is_valid=False,
                        reason_code="SEMANTIC_DUPLICATE",
                        reason_detail=f"Semantically similar to index {similar_idx} (similarity: {similarity:.3f})",
                        metadata={
                            "similar_to_index": similar_idx,
                            "similarity_score": similarity,
                            "threshold": self.config.semantic_threshold,
                            "pii_masked_count": len(pii_matches)
                        }
                    )

        # Gate 7: Contradiction detection
        if self.contradiction_detector:
            with self._dedup_lock:
                is_valid, contradicting_idx, confidence = self.contradiction_detector.add(text)
                if not is_valid:
                    self.stats["rejected_contradiction"] += 1
                    return FilterResult(
                        text=text,
                        original_text=original_text,
                        is_valid=False,
                        reason_code="CONTRADICTION",
                        reason_detail=f"Contradicts text at index {contradicting_idx} (confidence: {confidence:.3f})",
                        metadata={
                            "contradicting_index": contradicting_idx,
                            "contradiction_confidence": confidence,
                            "threshold": self.config.contradiction_threshold,
                            "pii_masked_count": len(pii_matches)
                        }
                    )

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

    def process_batch(
        self,
        texts: "List[Union[str, DocumentChunk]]",
        use_parallel: bool = False,
    ) -> BatchResult:
        """
        Process a batch of text chunks with optimized batching.

        Args:
            texts: List of strings or DocumentChunks (from a connector)
            use_parallel: Enable parallel processing (default: False for compatibility)

        Returns:
            BatchResult with accepted and rejected chunks
        """
        if use_parallel and self.config.parallel_workers > 1:
            return self._process_batch_parallel(texts)
        else:
            return self._process_batch_sequential(texts)

    def _process_batch_sequential(self, texts: "List[Union[str, DocumentChunk]]") -> BatchResult:
        """Process batch sequentially (original behavior)."""
        result = BatchResult()

        with self._stats_lock:
            self.stats["total_processed"] += len(texts)

        for item in texts:
            raw_text, source_metadata = self._normalize_input(item)
            original_text = raw_text

            # Process stateless gates
            processed_text, pii_matches, rejection = self._process_stateless_gates(raw_text, original_text)

            if rejection:
                rejection.source_metadata = source_metadata
                result.rejected.append(rejection)
            else:
                filter_result = self._process_stateful_gates(processed_text, original_text, pii_matches)
                filter_result.source_metadata = source_metadata
                if filter_result.is_valid:
                    result.accepted.append(filter_result)
                else:
                    result.rejected.append(filter_result)

        # Log rejected chunks to DLQ
        if self.dlq and result.rejected:
            self.dlq.log_batch(result.rejected)

        return result

    def _process_batch_parallel(self, texts: "List[Union[str, DocumentChunk]]") -> BatchResult:
        """
        Process batch with parallel workers for stateless gates.

        Stateless gates (length, PII, entropy) run in parallel.
        Stateful gates (deduplication) run sequentially with locks.
        """
        result = BatchResult()

        with self._stats_lock:
            self.stats["total_processed"] += len(texts)

        # Normalise once; keep source_metadata alongside raw text
        normalised = [self._normalize_input(item) for item in texts]

        batch_size = self.config.batch_size
        num_batches = (len(normalised) + batch_size - 1) // batch_size

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(normalised))
            batch = normalised[start_idx:end_idx]

            # Process stateless gates in parallel
            stateless_results: Dict[int, tuple] = {}
            with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
                futures = {
                    executor.submit(self._process_stateless_gates, raw_text, raw_text): (idx, raw_text, src_meta)
                    for idx, (raw_text, src_meta) in enumerate(batch)
                }

                for future in as_completed(futures):
                    idx, original_text, src_meta = futures[future]
                    try:
                        stateless_results[idx] = (*future.result(), src_meta)
                    except Exception as e:
                        stateless_results[idx] = (None, [], FilterResult(
                            text=original_text,
                            original_text=original_text,
                            is_valid=False,
                            reason_code="PROCESSING_ERROR",
                            reason_detail=f"Error during processing: {str(e)}",
                            metadata={},
                            source_metadata=src_meta,
                        ), src_meta)

            # Process stateful gates sequentially in original order
            for idx in sorted(stateless_results.keys()):
                processed_text, pii_matches, rejection, src_meta = stateless_results[idx]
                if rejection:
                    rejection.source_metadata = src_meta
                    result.rejected.append(rejection)
                else:
                    original_text = batch[idx][0]
                    filter_result = self._process_stateful_gates(processed_text, original_text, pii_matches)
                    filter_result.source_metadata = src_meta
                    if filter_result.is_valid:
                        result.accepted.append(filter_result)
                    else:
                        result.rejected.append(filter_result)

        # Log rejected chunks to DLQ
        if self.dlq and result.rejected:
            self.dlq.log_batch(result.rejected)

        return result

    def reset(self):
        """Reset all deduplicators and statistics."""
        if self.exact_dedup:
            self.exact_dedup.reset()

        if self.fuzzy_dedup:
            self.fuzzy_dedup.reset()

        if self.semantic_dedup:
            self.semantic_dedup.reset()

        if self.contradiction_detector:
            self.contradiction_detector.reset()

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
