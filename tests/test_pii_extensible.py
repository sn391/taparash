"""Tests for extensible PII detection (PIIDetector protocol + register_detector)."""

from typing import List
from taparash import PIIMasker, PIIMatch, PIIDetector


class FakeDetector:
    """A simple custom detector that flags any occurrence of 'SECRET' as PII."""

    def detect(self, text: str) -> List[PIIMatch]:
        import re
        matches = []
        for m in re.finditer(r'\bSECRET\b', text):
            matches.append(PIIMatch(
                pii_type="custom_secret",
                start=m.start(),
                end=m.end(),
                matched_text=m.group(),
            ))
        return matches


def test_register_detector_is_called():
    masker = PIIMasker(mask_emails=False, mask_phones=False, mask_credit_cards=False, mask_ssn=False)
    detector = FakeDetector()
    masker.register_detector(detector)

    matches = masker.detect_pii("The password is SECRET and should be flagged.")
    custom_matches = [m for m in matches if m.pii_type == "custom_secret"]
    assert len(custom_matches) == 1
    assert custom_matches[0].matched_text == "SECRET"


def test_registered_detector_masks():
    masker = PIIMasker(mask_emails=False, mask_phones=False, mask_credit_cards=False, mask_ssn=False)
    masker.register_detector(FakeDetector())

    masked_text, matches = masker.mask("Credential: SECRET found here.")
    assert "SECRET" not in masked_text
    assert "[REDACTED]" in masked_text


def test_unregister_detector():
    masker = PIIMasker(mask_emails=False, mask_phones=False, mask_credit_cards=False, mask_ssn=False)
    detector = FakeDetector()
    masker.register_detector(detector)
    masker.unregister_detector(detector)

    matches = masker.detect_pii("The value is SECRET.")
    custom_matches = [m for m in matches if m.pii_type == "custom_secret"]
    assert len(custom_matches) == 0


def test_multiple_detectors():
    class AnotherDetector:
        def detect(self, text: str) -> List[PIIMatch]:
            import re
            return [
                PIIMatch("codename", m.start(), m.end(), m.group())
                for m in re.finditer(r'\bCODENAME\b', text)
            ]

    masker = PIIMasker(mask_emails=False, mask_phones=False, mask_credit_cards=False, mask_ssn=False)
    masker.register_detector(FakeDetector())
    masker.register_detector(AnotherDetector())

    matches = masker.detect_pii("SECRET and CODENAME are both flagged.")
    types = {m.pii_type for m in matches}
    assert "custom_secret" in types
    assert "codename" in types


def test_crashing_detector_does_not_break_pipeline():
    class BadDetector:
        def detect(self, text: str) -> List[PIIMatch]:
            raise RuntimeError("intentional crash")

    masker = PIIMasker()
    masker.register_detector(BadDetector())
    # Should not raise; bad detector is silently skipped
    masked_text, _ = masker.mask("test@example.com is an email.")
    assert "[REDACTED]" in masked_text


def test_pii_detector_protocol_check():
    """FakeDetector satisfies the PIIDetector runtime-checkable protocol."""
    assert isinstance(FakeDetector(), PIIDetector)
