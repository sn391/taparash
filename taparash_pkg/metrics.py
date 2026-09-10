"""Lightweight metrics emitted after each pipeline call."""

from dataclasses import dataclass
from typing import Callable, Dict, Any


@dataclass
class PipelineMetrics:
    """
    Per-call snapshot emitted after every process_batch() / process_single() call.

    Assign a callback to QualityConfig.metrics_callback to receive these.
    Compatible with Prometheus, DataDog, StatsD, or any custom sink.
    """

    total: int = 0
    accepted: int = 0
    rejected_length: int = 0
    rejected_entropy: int = 0
    rejected_exact_dup: int = 0
    rejected_fuzzy_dup: int = 0
    rejected_semantic_dup: int = 0
    rejected_contradiction: int = 0
    pii_hits: int = 0          # total PII tokens redacted across all chunks in this call
    wall_time_ms: float = 0.0  # elapsed wall-clock time for the call

    @property
    def rejected(self) -> int:
        """Total rejected chunks."""
        return self.total - self.accepted

    @property
    def acceptance_rate(self) -> float:
        """Fraction of accepted chunks as a percentage (0-100)."""
        if self.total == 0:
            return 0.0
        return self.accepted / self.total * 100.0

    def as_dict(self) -> Dict[str, Any]:
        """Flat dict suitable for JSON logging or metric tag injection."""
        return {
            "total": self.total,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "rejected_length": self.rejected_length,
            "rejected_entropy": self.rejected_entropy,
            "rejected_exact_dup": self.rejected_exact_dup,
            "rejected_fuzzy_dup": self.rejected_fuzzy_dup,
            "rejected_semantic_dup": self.rejected_semantic_dup,
            "rejected_contradiction": self.rejected_contradiction,
            "pii_hits": self.pii_hits,
            "wall_time_ms": round(self.wall_time_ms, 3),
            "acceptance_rate": round(self.acceptance_rate, 2),
        }


# Type alias for the callback signature.
# Assign a function matching this signature to QualityConfig.metrics_callback.
MetricsCallback = Callable[[PipelineMetrics], None]
