"""Heuristic text-quality filters (Gopher / C4 rules).

All checks are pure Python with no ML models required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class QualityCheckResult:
    """Outcome of a heuristic quality check."""

    passed: bool
    reason_code: Optional[str] = None
    reason_detail: Optional[str] = None


class HeuristicQualityFilter:
    """
    Gopher- and C4-style heuristic text-quality filters.

    Three independent checks (all thresholds configurable):

    * ``line_length_ratio`` — fraction of lines exceeding *max_line_length*
      characters.  Long-line-heavy text is often code dumps, logs, or encoded
      blobs rather than natural language.

    * ``symbol_density`` — fraction of non-alphanumeric, non-whitespace
      characters.  High values indicate markdown/HTML noise, code, or
      obfuscated content.

    * ``word_repetition`` — fraction of total word tokens that are duplicates
      (i.e. ``(total - unique) / total``).  Catches spam patterns like
      "click click click buy now buy now".

    All checks are applied in sequence; the first failure short-circuits.
    """

    _WORD_RE = re.compile(r'\b\w+\b')

    def __init__(
        self,
        max_line_length: int = 1000,
        max_line_length_ratio: float = 0.3,
        max_symbol_density: float = 0.1,
        max_word_repetition_ratio: float = 0.5,
    ) -> None:
        """
        Args:
            max_line_length: Line length (chars) above which a line counts as
                "too long".  Default: 1000.
            max_line_length_ratio: Maximum allowed fraction of lines that are
                "too long".  Default: 0.30 (30 %).
            max_symbol_density: Maximum allowed fraction of non-alphanumeric,
                non-whitespace characters.  Default: 0.10 (10 %).
            max_word_repetition_ratio: Maximum allowed fraction of duplicate
                word tokens.  Default: 0.50 (50 %).
        """
        self.max_line_length = max_line_length
        self.max_line_length_ratio = max_line_length_ratio
        self.max_symbol_density = max_symbol_density
        self.max_word_repetition_ratio = max_word_repetition_ratio

    def check(self, text: str) -> QualityCheckResult:
        """Run all heuristic checks; return on first failure."""
        for check_fn in (
            self._check_line_length_ratio,
            self._check_symbol_density,
            self._check_word_repetition,
        ):
            result = check_fn(text)
            if not result.passed:
                return result
        return QualityCheckResult(passed=True)

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_line_length_ratio(self, text: str) -> QualityCheckResult:
        lines = text.splitlines()
        if not lines:
            return QualityCheckResult(passed=True)
        long_count = sum(1 for ln in lines if len(ln) > self.max_line_length)
        ratio = long_count / len(lines)
        if ratio > self.max_line_length_ratio:
            return QualityCheckResult(
                passed=False,
                reason_code="HIGH_LINE_LENGTH_RATIO",
                reason_detail=(
                    f"{ratio:.1%} of lines exceed {self.max_line_length} chars "
                    f"(threshold: {self.max_line_length_ratio:.1%})"
                ),
            )
        return QualityCheckResult(passed=True)

    def _check_symbol_density(self, text: str) -> QualityCheckResult:
        if not text:
            return QualityCheckResult(passed=True)
        symbol_count = sum(
            1 for ch in text if not ch.isalnum() and not ch.isspace()
        )
        density = symbol_count / len(text)
        if density > self.max_symbol_density:
            return QualityCheckResult(
                passed=False,
                reason_code="HIGH_SYMBOL_DENSITY",
                reason_detail=(
                    f"Symbol density {density:.1%} exceeds threshold "
                    f"{self.max_symbol_density:.1%}"
                ),
            )
        return QualityCheckResult(passed=True)

    def _check_word_repetition(self, text: str) -> QualityCheckResult:
        words = self._WORD_RE.findall(text.lower())
        if len(words) < 10:
            return QualityCheckResult(passed=True)
        duplicate_count = len(words) - len(set(words))
        ratio = duplicate_count / len(words)
        if ratio > self.max_word_repetition_ratio:
            return QualityCheckResult(
                passed=False,
                reason_code="HIGH_WORD_REPETITION",
                reason_detail=(
                    f"Word repetition ratio {ratio:.1%} exceeds threshold "
                    f"{self.max_word_repetition_ratio:.1%}"
                ),
            )
        return QualityCheckResult(passed=True)
