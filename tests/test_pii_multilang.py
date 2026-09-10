"""Tests for multi-language (European) PII detection patterns.

Covers IBAN (with mod-97 validation), EU VAT numbers, and European local
phone formats. All patterns are opt-in (default False) to avoid false positives.
"""

import pytest
from taparash import PIIMasker


# ---------------------------------------------------------------------------
# IBAN
# ---------------------------------------------------------------------------

class TestIBAN:
    def make_masker(self):
        return PIIMasker(
            mask_emails=False, mask_phones=False, mask_credit_cards=False,
            mask_ssn=False, mask_iban=True,
        )

    def test_compact_iban_detected(self):
        m = self.make_masker()
        text = "Bank account: GB29NWBK60161331926819 for payment."
        matches = m.detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == "iban"
        assert matches[0].matched_text == "GB29NWBK60161331926819"

    def test_formatted_iban_detected(self):
        m = self.make_masker()
        text = "IBAN: DE89 3704 0044 0532 0130 00"
        matches = m.detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == "iban"

    def test_multiple_country_ibans(self):
        m = self.make_masker()
        texts = [
            ("GB29NWBK60161331926819", True),   # UK — valid
            ("DE89370400440532013000", True),    # Germany — valid
            ("FR7630006000011234567890189", True),  # France — valid
            ("XX00FAKE00000000000000", False),   # fake country — invalid checksum
            ("GB00NWBK60161331926819", False),   # bad check digits
        ]
        for iban, should_match in texts:
            matches = m.detect_pii(f"Account {iban} here.")
            if should_match:
                assert len(matches) == 1, f"Expected match for {iban}"
                assert matches[0].matched_text == iban
            else:
                assert len(matches) == 0, f"Expected no match for {iban}"

    def test_iban_masked_in_text(self):
        m = self.make_masker()
        masked, matches = m.mask("Wire to GB29NWBK60161331926819 by Friday.")
        assert "GB29NWBK60161331926819" not in masked
        assert "[REDACTED]" in masked

    def test_iban_not_detected_by_default(self):
        m = PIIMasker()  # default: mask_iban=False
        matches = m.detect_pii("Account GB29NWBK60161331926819.")
        iban_matches = [x for x in matches if x.pii_type == "iban"]
        assert len(iban_matches) == 0

    def test_invalid_checksum_not_detected(self):
        m = self.make_masker()
        # Mutate last digit to break mod-97
        matches = m.detect_pii("Account GB29NWBK60161331926811 here.")
        assert len(matches) == 0

    def test_validate_iban_static_method(self):
        assert PIIMasker._validate_iban("GB29NWBK60161331926819") is True
        assert PIIMasker._validate_iban("GB29 NWBK 6016 1331 9268 19") is True  # spaced
        assert PIIMasker._validate_iban("DE89370400440532013000") is True
        assert PIIMasker._validate_iban("GB00NWBK60161331926819") is False
        assert PIIMasker._validate_iban("TOOSHORT") is False


# ---------------------------------------------------------------------------
# EU VAT
# ---------------------------------------------------------------------------

class TestEUVAT:
    def make_masker(self):
        return PIIMasker(
            mask_emails=False, mask_phones=False, mask_credit_cards=False,
            mask_ssn=False, mask_eu_vat=True,
        )

    def test_german_vat_detected(self):
        m = self.make_masker()
        matches = m.detect_pii("Supplier VAT: DE123456789")
        assert len(matches) == 1
        assert matches[0].pii_type == "eu_vat"
        assert matches[0].matched_text == "DE123456789"

    def test_french_vat_detected(self):
        m = self.make_masker()
        matches = m.detect_pii("TVA: FR12345678901")
        assert len(matches) == 1
        assert matches[0].pii_type == "eu_vat"

    def test_uk_vat_detected(self):
        m = self.make_masker()
        matches = m.detect_pii("VAT registration: GB123456789")
        assert len(matches) == 1
        assert matches[0].matched_text == "GB123456789"

    def test_dutch_vat_detected(self):
        m = self.make_masker()
        matches = m.detect_pii("BTW: NL123456789B01")
        assert len(matches) == 1
        assert matches[0].matched_text == "NL123456789B01"

    def test_multiple_vat_in_document(self):
        m = self.make_masker()
        text = "Buyer DE123456789 and seller IT12345678901 agreed."
        matches = m.detect_pii(text)
        assert len(matches) == 2
        types = {x.pii_type for x in matches}
        assert types == {"eu_vat"}

    def test_vat_masked_in_text(self):
        m = self.make_masker()
        masked, _ = m.mask("Invoice for DE123456789.")
        assert "DE123456789" not in masked
        assert "[REDACTED]" in masked

    def test_vat_not_detected_by_default(self):
        m = PIIMasker()  # default: mask_eu_vat=False
        matches = m.detect_pii("VAT DE123456789")
        vat_matches = [x for x in matches if x.pii_type == "eu_vat"]
        assert len(vat_matches) == 0


# ---------------------------------------------------------------------------
# European local phone numbers
# ---------------------------------------------------------------------------

class TestEULocalPhone:
    def make_masker(self):
        return PIIMasker(
            mask_emails=False, mask_phones=False, mask_credit_cards=False,
            mask_ssn=False, mask_eu_phone=True,
        )

    def test_uk_mobile_detected(self):
        m = self.make_masker()
        matches = m.detect_pii("Call 07911 123456 for support.")
        assert len(matches) == 1
        assert matches[0].pii_type == "eu_phone"

    def test_uk_landline_detected(self):
        m = self.make_masker()
        matches = m.detect_pii("Office: 01234 567890")
        assert len(matches) == 1
        assert matches[0].pii_type == "eu_phone"

    def test_french_local_phone_detected(self):
        m = self.make_masker()
        matches = m.detect_pii("Appelez le 06 12 34 56 78.")
        assert len(matches) == 1
        assert matches[0].pii_type == "eu_phone"

    def test_eu_phone_masked(self):
        m = self.make_masker()
        masked, _ = m.mask("Contact 07911 123456 for help.")
        assert "07911 123456" not in masked
        assert "[REDACTED]" in masked

    def test_eu_phone_not_detected_by_default(self):
        m = PIIMasker()  # default: mask_eu_phone=False
        matches = m.detect_pii("Call 07911 123456")
        eu_matches = [x for x in matches if x.pii_type == "eu_phone"]
        assert len(eu_matches) == 0


# ---------------------------------------------------------------------------
# Integration: all EU patterns together via QualityConfig
# ---------------------------------------------------------------------------

class TestQualityConfigIntegration:
    def test_eu_flags_wired_through_pipeline(self):
        from taparash import TaparashFilter, QualityConfig

        config = QualityConfig(
            enable_pii_masking=True,
            pii_mask_iban=True,
            pii_mask_eu_vat=True,
            pii_mask_eu_phone=True,
            entropy_threshold=5.5,
            enable_dlq=False,
        )
        f = TaparashFilter(config)
        result = f.process_single(
            "Send payment to GB29NWBK60161331926819, VAT DE123456789, call 07911 123456."
        )
        assert result.is_valid
        assert "GB29NWBK60161331926819" not in result.text
        assert "DE123456789" not in result.text
        assert "07911 123456" not in result.text
        assert result.text.count("[REDACTED]") == 3
