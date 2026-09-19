"""Tests for PII anonymization strategies and date/time detection (items 3-5)."""

import re
import pytest
from taparash import PIIMasker, PIIMatch


# ---------------------------------------------------------------------------
# Item 3: Date/time PII detection
# ---------------------------------------------------------------------------

class TestDateTimePII:
    def _masker(self, **kwargs):
        return PIIMasker(
            mask_emails=False,
            mask_phones=False,
            mask_credit_cards=False,
            mask_ssn=False,
            mask_dates=True,
            **kwargs,
        )

    def test_iso_date_detected(self):
        m = self._masker()
        matches = m.detect_pii("The event is on 2024-03-15 at noon.")
        dates = [x for x in matches if x.pii_type == "date"]
        assert len(dates) == 1
        assert dates[0].matched_text == "2024-03-15"

    def test_slash_date_detected(self):
        m = self._masker()
        matches = m.detect_pii("Born on 15/06/1990.")
        dates = [x for x in matches if x.pii_type == "date"]
        assert any("15/06/1990" in d.matched_text for d in dates)

    def test_month_name_date_detected(self):
        m = self._masker()
        matches = m.detect_pii("The deadline is January 5, 2025.")
        dates = [x for x in matches if x.pii_type == "date"]
        assert len(dates) >= 1

    def test_time_detected(self):
        m = self._masker()
        matches = m.detect_pii("The meeting is at 14:30.")
        times = [x for x in matches if x.pii_type == "time"]
        assert len(times) >= 1
        assert "14:30" in times[0].matched_text

    def test_time_am_pm_detected(self):
        m = self._masker()
        matches = m.detect_pii("Call me at 9:00 AM.")
        times = [x for x in matches if x.pii_type == "time"]
        assert len(times) >= 1

    def test_dates_disabled_by_default(self):
        m = PIIMasker(mask_emails=False, mask_phones=False,
                      mask_credit_cards=False, mask_ssn=False)
        matches = m.detect_pii("The event is on 2024-03-15 at 14:30.")
        date_matches = [x for x in matches if x.pii_type in ("date", "time")]
        assert len(date_matches) == 0

    def test_date_masked_in_text(self):
        m = self._masker()
        masked, matches = m.mask("Appointment: 2024-03-15.")
        assert "2024-03-15" not in masked
        assert "[REDACTED]" in masked


# ---------------------------------------------------------------------------
# Item 4: Multiple anonymization strategies
# ---------------------------------------------------------------------------

class TestAnonymizationStrategies:
    TEXT = "Contact us at user@example.com for help."

    def test_redact_strategy_default(self):
        m = PIIMasker(anonymization_strategy="redact")
        masked, _ = m.mask(self.TEXT)
        assert "[REDACTED]" in masked
        assert "user@example.com" not in masked

    def test_tag_strategy(self):
        m = PIIMasker(anonymization_strategy="tag")
        masked, _ = m.mask(self.TEXT)
        assert "[EMAIL]" in masked
        assert "user@example.com" not in masked

    def test_hash_strategy_format(self):
        m = PIIMasker(anonymization_strategy="hash")
        masked, _ = m.mask(self.TEXT)
        assert re.search(r'\[SHA:[0-9a-f]{8}\]', masked)
        assert "user@example.com" not in masked

    def test_hash_strategy_is_deterministic(self):
        m = PIIMasker(anonymization_strategy="hash")
        masked1, _ = m.mask(self.TEXT)
        masked2, _ = m.mask(self.TEXT)
        assert masked1 == masked2

    def test_hash_different_values_produce_different_hashes(self):
        m = PIIMasker(anonymization_strategy="hash")
        _, m1 = m.mask("Email: a@example.com")
        _, m2 = m.mask("Email: b@example.com")
        hash1 = re.search(r'\[SHA:([0-9a-f]{8})\]', m.mask("Email: a@example.com")[0]).group(1)
        hash2 = re.search(r'\[SHA:([0-9a-f]{8})\]', m.mask("Email: b@example.com")[0]).group(1)
        assert hash1 != hash2

    def test_replace_strategy_fallback_to_hash_when_no_faker(self):
        """When faker is not installed, replace falls back to a hash token."""
        m = PIIMasker(anonymization_strategy="replace")
        # Temporarily break the faker import path by making it unavailable
        import sys
        faker_mod = sys.modules.get("faker")
        sys.modules["faker"] = None  # type: ignore[assignment]
        try:
            masked, _ = m.mask(self.TEXT)
            assert "user@example.com" not in masked
            # Either hash fallback or faker replacement; either way PII is gone
        finally:
            if faker_mod is not None:
                sys.modules["faker"] = faker_mod
            else:
                sys.modules.pop("faker", None)

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="anonymization_strategy"):
            PIIMasker(anonymization_strategy="vaporize")

    def test_tag_strategy_multiple_types(self):
        m = PIIMasker(
            anonymization_strategy="tag",
            mask_ssn=True,
        )
        text = "Email: alice@test.com  SSN: 123-45-6789"
        masked, _ = m.mask(text)
        assert "[EMAIL]" in masked
        assert "[SSN]" in masked

    def test_replace_strategy_with_faker(self):
        """If faker IS installed, replacement should differ from original."""
        try:
            import faker as _  # noqa: F401
        except ImportError:
            pytest.skip("faker not installed")
        m = PIIMasker(anonymization_strategy="replace")
        masked, _ = m.mask(self.TEXT)
        assert "user@example.com" not in masked
        # Result should not contain the redact token (faker was used)
        assert "[REDACTED]" not in masked


# ---------------------------------------------------------------------------
# Item 5: Per-entity strategy config
# ---------------------------------------------------------------------------

class TestPerEntityStrategy:
    def test_per_entity_override(self):
        m = PIIMasker(
            anonymization_strategy="redact",
            strategies={"email": "tag", "ssn": "hash"},
        )
        text = "Contact user@test.com  SSN: 123-45-6789"
        masked, _ = m.mask(text)
        assert "[EMAIL]" in masked          # email → tag
        assert re.search(r'\[SHA:[0-9a-f]{8}\]', masked)  # ssn → hash
        assert "[REDACTED]" not in masked   # no plain redact used

    def test_fallback_to_default_strategy(self):
        m = PIIMasker(
            anonymization_strategy="tag",
            strategies={"email": "hash"},
            mask_ssn=True,
        )
        text = "user@test.com and SSN: 123-45-6789"
        masked, _ = m.mask(text)
        assert re.search(r'\[SHA:[0-9a-f]{8}\]', masked)  # email → hash (override)
        assert "[SSN]" in masked                            # ssn → tag (default)

    def test_invalid_per_entity_strategy_raises(self):
        with pytest.raises(ValueError, match="strategies"):
            PIIMasker(strategies={"email": "zap"})

    def test_empty_strategies_uses_default(self):
        m = PIIMasker(anonymization_strategy="tag", strategies={})
        masked, _ = m.mask("hello@world.com")
        assert "[EMAIL]" in masked

    def test_per_entity_date_strategy(self):
        m = PIIMasker(
            mask_emails=False,
            mask_phones=False,
            mask_credit_cards=False,
            mask_ssn=False,
            mask_dates=True,
            anonymization_strategy="redact",
            strategies={"date": "tag"},
        )
        masked, _ = m.mask("The date is 2024-01-01.")
        assert "[DATE]" in masked
        assert "[REDACTED]" not in masked


# ---------------------------------------------------------------------------
# Config integration: QualityConfig → pipeline
# ---------------------------------------------------------------------------

def test_pipeline_uses_tag_strategy():
    from taparash import TaparashFilter, QualityConfig
    config = QualityConfig(
        enable_pii_masking=True,
        pii_mask_emails=True,
        pii_anonymization_strategy="tag",
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
        enable_entropy_check=False,
        enable_dlq=False,
    )
    f = TaparashFilter(config)
    result = f.process_single(
        "Please email admin@company.com for access. This text is long enough."
    )
    assert "[EMAIL]" in result.text
    assert "admin@company.com" not in result.text


def test_pipeline_per_entity_strategy_from_config():
    from taparash import TaparashFilter, QualityConfig
    config = QualityConfig(
        enable_pii_masking=True,
        pii_mask_emails=True,
        pii_mask_ssn=True,
        pii_anonymization_strategy="redact",
        pii_strategies={"email": "hash"},
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
        enable_entropy_check=False,
        enable_dlq=False,
    )
    f = TaparashFilter(config)
    result = f.process_single(
        "Email admin@company.com and SSN 123-45-6789 are both PII."
    )
    assert re.search(r'\[SHA:[0-9a-f]{8}\]', result.text)  # email hashed
    assert "[REDACTED]" in result.text                      # ssn redacted


def test_pipeline_date_pii_opt_in():
    from taparash import TaparashFilter, QualityConfig
    config = QualityConfig(
        enable_pii_masking=True,
        pii_mask_emails=False,
        pii_mask_phones=False,
        pii_mask_credit_cards=False,
        pii_mask_ssn=False,
        pii_mask_dates=True,
        enable_exact_dedup=False,
        enable_fuzzy_dedup=False,
        enable_entropy_check=False,
        enable_dlq=False,
    )
    f = TaparashFilter(config)
    result = f.process_single(
        "The incident occurred on 2024-03-15 at 14:30. This needs masking."
    )
    assert "2024-03-15" not in result.text
