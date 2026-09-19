"""Language identification gate.

Optional dependency: ``langdetect`` (pip install langdetect, or
pip install taparash[langid]).  When the package is not installed the
filter is a transparent no-op — every chunk passes — so the pipeline
never breaks on a missing optional dependency.
"""

from __future__ import annotations

from typing import List, Optional

try:
    from langdetect import detect as _ld_detect
    from langdetect.lang_detect_exception import LangDetectException as _LDE
    _LANGDETECT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LANGDETECT_AVAILABLE = False
    _ld_detect = None  # type: ignore[assignment]
    _LDE = Exception  # type: ignore[assignment,misc]


class LanguageFilter:
    """
    Filter text chunks by detected language.

    Uses ``langdetect`` under the hood (a fast, fully offline statistical
    language identifier supporting 55 languages).  When ``langdetect`` is
    not installed, :meth:`is_allowed` always returns ``True`` so the
    pipeline continues unaffected.

    Args:
        allowed_languages: ISO 639-1 language codes to accept
            (e.g. ``["en"]``, ``["en", "de", "fr"]``).
            Defaults to English only.
    """

    def __init__(self, allowed_languages: Optional[List[str]] = None) -> None:
        self.allowed_languages: List[str] = list(allowed_languages or ["en"])
        self._available: bool = _LANGDETECT_AVAILABLE

    @property
    def available(self) -> bool:
        """True when ``langdetect`` is installed and usable."""
        return self._available

    def detect(self, text: str) -> Optional[str]:
        """
        Return the detected ISO 639-1 language code, or ``None`` on failure.

        Returns ``None`` when langdetect is unavailable, the text is too
        short, or detection is inconclusive.
        """
        if not self._available or not text.strip():
            return None
        try:
            return _ld_detect(text)
        except _LDE:
            return None

    def is_allowed(self, text: str) -> bool:
        """
        Return ``True`` if the text is in an allowed language.

        Defaults to ``True`` when:
        * ``langdetect`` is not installed (graceful degradation).
        * Detection returns ``None`` (too short or ambiguous text).
        """
        if not self._available:
            return True
        lang = self.detect(text)
        if lang is None:
            return True
        return lang in self.allowed_languages
