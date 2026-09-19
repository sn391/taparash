"""Tests for heuristic quality rules (item 1: Gopher/C4 filters)."""

import pytest
from taparash import HeuristicQualityFilter, QualityCheckResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_filter():
    return HeuristicQualityFilter()


# ---------------------------------------------------------------------------
# Line-length ratio
# ---------------------------------------------------------------------------

def test_line_length_ratio_passes_normal_text(default_filter):
    text = "Hello world\nThis is a normal sentence.\nShort lines."
    result = default_filter.check(text)
    assert result.passed


def test_line_length_ratio_rejects_long_lines():
    f = HeuristicQualityFilter(max_line_length=20, max_line_length_ratio=0.3)
    # 2 out of 3 lines are too long → 66.7 % > 30 %
    long_line = "x" * 50
    text = f"{long_line}\n{long_line}\nshort"
    result = f.check(text)
    assert not result.passed
    assert result.reason_code == "HIGH_LINE_LENGTH_RATIO"


def test_line_length_ratio_exact_threshold():
    f = HeuristicQualityFilter(max_line_length=10, max_line_length_ratio=0.5)
    # Exactly 50 % long lines → should pass (not strictly greater than)
    text = "x" * 20 + "\nshort"
    result = f.check(text)
    assert result.passed


# ---------------------------------------------------------------------------
# Symbol density
# ---------------------------------------------------------------------------

def test_symbol_density_passes_normal_text(default_filter):
    result = default_filter.check("Hello, world! This is normal text.")
    assert result.passed


def test_symbol_density_rejects_high_symbol_text():
    f = HeuristicQualityFilter(max_symbol_density=0.05)
    # Mostly symbols: "!!!@@###$$$%%%^^^&&&***(((" etc.
    text = "!!@@##$$%%^^&&**((!!@@##$$%%^^&&**" * 3 + " some words here"
    result = f.check(text)
    assert not result.passed
    assert result.reason_code == "HIGH_SYMBOL_DENSITY"


def test_symbol_density_empty_text(default_filter):
    result = default_filter.check("")
    assert result.passed


# ---------------------------------------------------------------------------
# Word repetition
# ---------------------------------------------------------------------------

def test_word_repetition_passes_natural_text(default_filter):
    text = (
        "The quick brown fox jumps over the lazy dog. "
        "A sample sentence with varied vocabulary to test repetition detection."
    )
    result = default_filter.check(text)
    assert result.passed


def test_word_repetition_rejects_spam():
    f = HeuristicQualityFilter(max_word_repetition_ratio=0.5)
    # "click" repeated 10 times out of 12 words → 9/12 ≈ 0.75 > 0.5
    text = "click " * 10 + "buy now"
    result = f.check(text)
    assert not result.passed
    assert result.reason_code == "HIGH_WORD_REPETITION"


def test_word_repetition_skips_short_text(default_filter):
    # Fewer than 10 words → check skipped
    result = default_filter.check("click click click click")
    assert result.passed


# ---------------------------------------------------------------------------
# Combined / ordering
# ---------------------------------------------------------------------------

def test_first_failure_short_circuits():
    """Line-length check fires before word-repetition; only one reason returned."""
    f = HeuristicQualityFilter(
        max_line_length=5,
        max_line_length_ratio=0.0,  # any long line fails
        max_word_repetition_ratio=0.5,
    )
    text = "this line is too long\n" + "click " * 15
    result = f.check(text)
    assert not result.passed
    assert result.reason_code == "HIGH_LINE_LENGTH_RATIO"


def test_result_is_dataclass():
    f = HeuristicQualityFilter()
    result = f.check("hello world")
    assert isinstance(result, QualityCheckResult)


# ---------------------------------------------------------------------------
# Integration: QualityConfig + TaparashFilter pipeline
# ---------------------------------------------------------------------------

def test_pipeline_heuristic_gate_rejects():
    from taparash import TaparashFilter, QualityConfig
    config = QualityConfig(
        enable_heuristic_quality=True,
        heuristic_max_symbol_density=0.05,
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
        enable_entropy_check=False,
        enable_pii_masking=False,
        enable_dlq=False,
    )
    f = TaparashFilter(config)
    spam = "!!!@@##$$$%%^^^&&& " * 5 + "words"
    result = f.process_single(spam)
    assert not result.is_valid
    assert result.reason_code == "HIGH_SYMBOL_DENSITY"
    assert f.stats["rejected_heuristic_quality"] == 1


def test_pipeline_heuristic_gate_disabled_by_default():
    from taparash import TaparashFilter, QualityConfig
    config = QualityConfig(
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
        enable_entropy_check=False,
        enable_pii_masking=False,
        enable_dlq=False,
    )
    f = TaparashFilter(config)
    spam = "!!!@@##$$$%%^^^&&&" * 5 + "words here"
    result = f.process_single(spam)
    # Gate disabled → chunk passes (or fails on other gates, but not heuristic)
    assert result.reason_code != "HIGH_SYMBOL_DENSITY"
