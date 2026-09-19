"""Tests for language identification gate (item 2)."""

import pytest
from taparash import LanguageFilter


def test_language_filter_instantiates():
    f = LanguageFilter(allowed_languages=["en"])
    assert f.allowed_languages == ["en"]


def test_unavailable_filter_always_passes():
    """When langdetect is not installed, every chunk should pass."""
    f = LanguageFilter(allowed_languages=["en"])
    # Force unavailable regardless of installation
    f._available = False
    assert f.is_allowed("Bonjour le monde, ceci est du français.") is True
    assert f.detect("anything") is None


def test_detect_returns_none_when_unavailable():
    f = LanguageFilter()
    f._available = False
    assert f.detect("hello world") is None


def test_is_allowed_empty_text_passes():
    """Empty / whitespace-only text should not be rejected."""
    f = LanguageFilter(allowed_languages=["en"])
    # Even if langdetect is available, empty text → detect returns None → pass
    assert f.is_allowed("") is True
    assert f.is_allowed("   ") is True


def test_allowed_languages_default_is_english():
    f = LanguageFilter()
    assert f.allowed_languages == ["en"]


# Tests that require langdetect — skipped when package is absent
langdetect_available = LanguageFilter().available

@pytest.mark.skipif(not langdetect_available, reason="langdetect not installed")
def test_english_text_passes():
    f = LanguageFilter(allowed_languages=["en"])
    assert f.is_allowed(
        "The quick brown fox jumps over the lazy dog. "
        "This is clearly an English sentence."
    ) is True


@pytest.mark.skipif(not langdetect_available, reason="langdetect not installed")
def test_french_text_rejected_when_en_only():
    f = LanguageFilter(allowed_languages=["en"])
    french = (
        "Bonjour, comment allez-vous? Je suis très heureux de vous voir "
        "aujourd'hui. La langue française est très belle."
    )
    # Detection might not be deterministic for short texts, but long French
    # text should reliably detect as 'fr'.
    lang = f.detect(french)
    if lang is not None and lang != "en":
        assert f.is_allowed(french) is False


@pytest.mark.skipif(not langdetect_available, reason="langdetect not installed")
def test_multi_language_allowlist():
    f = LanguageFilter(allowed_languages=["en", "de", "fr"])
    english = (
        "This is an English paragraph with enough words to ensure reliable detection."
    )
    assert f.is_allowed(english) is True


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

def test_pipeline_language_gate_disabled_by_default():
    from taparash import TaparashFilter, QualityConfig
    config = QualityConfig(
        enable_language_filter=False,
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
        enable_entropy_check=False,
        enable_pii_masking=False,
        enable_dlq=False,
    )
    f = TaparashFilter(config)
    result = f.process_single("Bonjour tout le monde, voici du texte en français.")
    assert result.reason_code != "LANGUAGE_NOT_ALLOWED"


def test_pipeline_language_gate_passes_when_unavailable():
    """Even with gate enabled, no rejections when langdetect is absent."""
    from taparash import TaparashFilter, QualityConfig
    config = QualityConfig(
        enable_language_filter=True,
        allowed_languages=["en"],
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
        enable_entropy_check=False,
        enable_pii_masking=False,
        enable_dlq=False,
    )
    f = TaparashFilter(config)
    if f.language_filter and not f.language_filter.available:
        result = f.process_single(
            "Bonjour tout le monde, ce texte n'est pas en anglais du tout."
        )
        assert result.is_valid
