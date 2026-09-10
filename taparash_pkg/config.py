"""Configuration management for Taparash."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List


@dataclass
class DocumentChunk:
    """
    A text chunk with structural metadata from a source document.

    Used by connectors (PDF, HTML, DOCX, PPTX) to carry provenance
    through the pipeline so rejection audit records include source context.
    """

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Common metadata keys populated by connectors:
    #   source_file: str      - original file path or URL
    #   format: str           - "pdf" | "html" | "pptx" | "docx"
    #   page_num: int         - 1-indexed page number (PDF, DOCX)
    #   slide_num: int        - 1-indexed slide number (PPTX)
    #   heading: str          - nearest section heading
    #   is_table: bool        - True when chunk came from a table cell


@dataclass
class QualityConfig:
    """
    Quality control configuration for Taparash filtering pipeline.

    All processing is 100% offline with zero external API calls.
    """

    # Length constraints
    min_chunk_length: int = 20
    max_chunk_length: int = 2000

    # Entropy filtering
    entropy_threshold: float = 4.2
    enable_entropy_check: bool = True

    # Deduplication
    enable_exact_dedup: bool = True
    enable_fuzzy_dedup: bool = True
    dedup_threshold: float = 0.88
    fuzzy_num_perm: int = 128
    fuzzy_shingle_size: int = 3
    use_word_shingles: bool = True

    # Semantic filtering (requires local models)
    enable_semantic_dedup: bool = False
    semantic_threshold: float = 0.90

    # Contradiction detection (requires NLI model)
    check_contradictions: bool = False
    contradiction_threshold: float = 0.7

    # PII masking
    enable_pii_masking: bool = True
    pii_mask_emails: bool = True
    pii_mask_phones: bool = True
    pii_mask_credit_cards: bool = True
    pii_mask_ssn: bool = True
    pii_replacement_token: str = "[REDACTED]"

    # Dead Letter Queue
    enable_dlq: bool = True
    dlq_path: Optional[str] = None

    # Processing options
    batch_size: int = 100
    parallel_workers: int = 4

    # Model paths (for offline models)
    embeddings_model_path: Optional[str] = None
    nli_model_path: Optional[str] = None

    def validate(self) -> List[str]:
        """
        Validate configuration parameters.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if self.min_chunk_length < 1:
            errors.append("min_chunk_length must be >= 1")

        if self.max_chunk_length < self.min_chunk_length:
            errors.append("max_chunk_length must be >= min_chunk_length")

        if not 0.0 <= self.entropy_threshold <= 10.0:
            errors.append("entropy_threshold must be between 0.0 and 10.0")

        if not 0.0 <= self.dedup_threshold <= 1.0:
            errors.append("dedup_threshold must be between 0.0 and 1.0")

        if not 0.0 <= self.semantic_threshold <= 1.0:
            errors.append("semantic_threshold must be between 0.0 and 1.0")

        if not 0.0 <= self.contradiction_threshold <= 1.0:
            errors.append("contradiction_threshold must be between 0.0 and 1.0")

        if self.fuzzy_num_perm < 16:
            errors.append("fuzzy_num_perm must be >= 16")

        if self.fuzzy_shingle_size < 1:
            errors.append("fuzzy_shingle_size must be >= 1")

        if self.batch_size < 1:
            errors.append("batch_size must be >= 1")

        if self.parallel_workers < 1:
            errors.append("parallel_workers must be >= 1")

        if self.enable_semantic_dedup and not self.embeddings_model_path:
            errors.append("embeddings_model_path required when enable_semantic_dedup=True")

        if self.check_contradictions and not self.nli_model_path:
            errors.append("nli_model_path required when check_contradictions=True")

        return errors

    def __post_init__(self):
        """Validate configuration after initialization."""
        errors = self.validate()
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


@dataclass
class FilterResult:
    """Result of filtering a single text chunk."""

    text: str
    original_text: str
    is_valid: bool
    reason_code: Optional[str] = None
    reason_detail: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure metadata is a dict."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BatchResult:
    """Result of filtering a batch of text chunks."""

    accepted: List[FilterResult] = field(default_factory=list)
    rejected: List[FilterResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of chunks processed."""
        return len(self.accepted) + len(self.rejected)

    @property
    def acceptance_rate(self) -> float:
        """Percentage of chunks accepted."""
        if self.total == 0:
            return 0.0
        return (len(self.accepted) / self.total) * 100

    def summary(self) -> str:
        """Get summary statistics."""
        return (
            f"Processed: {self.total} chunks\n"
            f"Accepted: {len(self.accepted)} ({self.acceptance_rate:.1f}%)\n"
            f"Rejected: {len(self.rejected)}"
        )
