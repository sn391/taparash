"""PII detection and masking using regex patterns."""

import re
from typing import List, Tuple, Dict, Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class PIIMatch:
    """Represents a detected PII match."""

    pii_type: str
    start: int
    end: int
    matched_text: str


@runtime_checkable
class PIIDetector(Protocol):
    """
    Protocol for custom PII detectors that extend PIIMasker.

    Implement ``detect(text)`` returning a list of PIIMatch objects, then
    register with ``PIIMasker.register_detector(your_detector)``.  Custom
    detectors run after all built-in regex patterns and their results are
    merged and sorted by start offset.

    Example::

        class SpacyNERDetector:
            def __init__(self, nlp):
                self.nlp = nlp

            def detect(self, text: str) -> List[PIIMatch]:
                doc = self.nlp(text)
                return [
                    PIIMatch(ent.label_.lower(), ent.start_char, ent.end_char, ent.text)
                    for ent in doc.ents
                    if ent.label_ in {"PERSON", "ORG", "GPE"}
                ]

        masker = PIIMasker()
        masker.register_detector(SpacyNERDetector(spacy.load("en_core_web_sm")))
    """

    def detect(self, text: str) -> List[PIIMatch]:
        """Detect PII in text; return list of PIIMatch, sorted by start offset."""
        ...


class PIIMasker:
    """
    Detect and mask Personally Identifiable Information (PII) using regex.

    100% offline operation with no external API calls.
    """

    # Email regex pattern
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Phone number patterns (US, international formats)
    PHONE_PATTERN = re.compile(
        r'(?:\+?1[-.\s]?)?'  # Optional country code
        r'(?:\([0-9]{3}\)|[0-9]{3})[-.\s]?'  # Area code
        r'[0-9]{3}[-.\s]?[0-9]{4}'  # Number
        r'|'
        r'\+[0-9]{1,3}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}'  # International
    )

    # Credit card patterns (Visa, MasterCard, Amex, Discover)
    CREDIT_CARD_PATTERN = re.compile(
        r'\b(?:'
        r'4[0-9]{12}(?:[0-9]{3})?|'  # Visa
        r'5[1-5][0-9]{14}|'  # MasterCard
        r'3[47][0-9]{13}|'  # Amex
        r'6(?:011|5[0-9]{2})[0-9]{12}'  # Discover
        r')\b'
    )

    # SSN pattern (US)
    SSN_PATTERN = re.compile(
        r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'
    )

    # Additional patterns for various IDs
    PASSPORT_PATTERN = re.compile(
        r'\b[A-Z]{1,2}[0-9]{6,9}\b'
    )

    # IP Address pattern
    IP_PATTERN = re.compile(
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    )

    # Credit card with spaces/dashes
    CREDIT_CARD_SPACED_PATTERN = re.compile(
        r'\b[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b'
    )

    # IBAN — compact (GB29NWBK60161331926819) and space-formatted (GB29 NWBK 6016 ...)
    IBAN_COMPACT_PATTERN = re.compile(
        r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b'
    )
    IBAN_FORMATTED_PATTERN = re.compile(
        r'\b[A-Z]{2}\d{2}(?:\s[A-Z0-9]{4}){2,7}(?:\s[A-Z0-9]{1,4})?\b'
    )

    # EU VAT registration numbers (all 27 EU member states + UK/NO)
    EU_VAT_PATTERN = re.compile(
        r'\b(?:'
        r'ATU\d{8}|'                            # Austria
        r'BE0?\d{9}|'                            # Belgium
        r'BG\d{9,10}|'                           # Bulgaria
        r'CY\d{8}[A-Z]|'                         # Cyprus
        r'CZ\d{8,10}|'                           # Czech Republic
        r'DE\d{9}|'                              # Germany
        r'DK\d{8}|'                              # Denmark
        r'EE\d{9}|'                              # Estonia
        r'EL\d{9}|'                              # Greece
        r'ES[A-Z0-9]\d{7}[A-Z0-9]|'             # Spain
        r'FI\d{8}|'                              # Finland
        r'FR[A-HJ-NP-Z0-9]{2}\d{9}|'            # France (letters I/O excluded)
        r'GB(?:\d{9}|\d{12}|GD\d{3}|HA\d{3})|'  # United Kingdom
        r'HR\d{11}|'                             # Croatia
        r'HU\d{8}|'                              # Hungary
        r'IE\d{7}[A-W](?:[A-I])?|'              # Ireland
        r'IT\d{11}|'                             # Italy
        r'LT(?:\d{9}|\d{12})|'                  # Lithuania
        r'LU\d{8}|'                              # Luxembourg
        r'LV\d{11}|'                             # Latvia
        r'MT\d{8}|'                              # Malta
        r'NL\d{9}B\d{2}|'                        # Netherlands
        r'PL\d{10}|'                             # Poland
        r'PT\d{9}|'                              # Portugal
        r'RO\d{2,10}|'                           # Romania
        r'SE\d{12}|'                             # Sweden
        r'SI\d{8}|'                              # Slovenia
        r'SK\d{10}'                              # Slovakia
        r')\b'
    )

    # European local phone formats (without +CC prefix, which the existing pattern covers)
    EU_LOCAL_PHONE_PATTERN = re.compile(
        r'\b(?:'
        r'07\d{3}[\s-]?\d{6}|'         # UK mobile (07xxx xxxxxx)
        r'0[12]\d{3}[\s-]?\d{6}|'      # UK landline (01xxx/02xxx xxxxxx)
        r'0[1-9](?:[\s.-]\d{2}){4}|'   # France (0X XX XX XX XX)
        r'0\d{2,4}[\s/-]\d{4,9}'       # Germany (0XX/XXXXXXXX)
        r')\b'
    )

    def __init__(
        self,
        mask_emails: bool = True,
        mask_phones: bool = True,
        mask_credit_cards: bool = True,
        mask_ssn: bool = True,
        mask_ip_addresses: bool = False,
        mask_iban: bool = False,
        mask_eu_vat: bool = False,
        mask_eu_phone: bool = False,
        replacement_token: str = "[REDACTED]"  # nosec B107 - masking token, not a password
    ):
        """
        Initialize PII masker.

        Args:
            mask_emails: Mask email addresses
            mask_phones: Mask phone numbers
            mask_credit_cards: Mask credit card numbers
            mask_ssn: Mask Social Security Numbers
            mask_ip_addresses: Mask IP addresses
            replacement_token: Token to use for masked PII
        """
        self.mask_emails = mask_emails
        self.mask_phones = mask_phones
        self.mask_credit_cards = mask_credit_cards
        self.mask_ssn = mask_ssn
        self.mask_ip_addresses = mask_ip_addresses
        self.mask_iban = mask_iban
        self.mask_eu_vat = mask_eu_vat
        self.mask_eu_phone = mask_eu_phone
        self.replacement_token = replacement_token
        self._custom_detectors: List[PIIDetector] = []

    def register_detector(self, detector: PIIDetector) -> None:
        """
        Register a custom PII detector alongside built-in regex patterns.

        Args:
            detector: Any object implementing the PIIDetector protocol
                      (has a ``detect(text) -> List[PIIMatch]`` method).
        """
        self._custom_detectors.append(detector)

    def unregister_detector(self, detector: PIIDetector) -> None:
        """
        Remove a previously registered custom detector.

        Args:
            detector: The detector instance to remove.

        Raises:
            ValueError: If the detector is not registered.
        """
        self._custom_detectors.remove(detector)

    def detect_pii(self, text: str) -> List[PIIMatch]:
        """
        Detect all PII in text without masking.

        Args:
            text: Input text string

        Returns:
            List of PIIMatch objects
        """
        matches = []

        if self.mask_emails:
            for match in self.EMAIL_PATTERN.finditer(text):
                matches.append(PIIMatch(
                    pii_type="email",
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group()
                ))

        if self.mask_phones:
            for match in self.PHONE_PATTERN.finditer(text):
                matches.append(PIIMatch(
                    pii_type="phone",
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group()
                ))

        if self.mask_credit_cards:
            for match in self.CREDIT_CARD_PATTERN.finditer(text):
                if self._validate_luhn(match.group()):
                    matches.append(PIIMatch(
                        pii_type="credit_card",
                        start=match.start(),
                        end=match.end(),
                        matched_text=match.group()
                    ))

            for match in self.CREDIT_CARD_SPACED_PATTERN.finditer(text):
                cleaned = re.sub(r'[\s-]', '', match.group())
                if self._validate_luhn(cleaned):
                    matches.append(PIIMatch(
                        pii_type="credit_card",
                        start=match.start(),
                        end=match.end(),
                        matched_text=match.group()
                    ))

        if self.mask_ssn:
            for match in self.SSN_PATTERN.finditer(text):
                matches.append(PIIMatch(
                    pii_type="ssn",
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group()
                ))

        if self.mask_ip_addresses:
            for match in self.IP_PATTERN.finditer(text):
                if self._validate_ip(match.group()):
                    matches.append(PIIMatch(
                        pii_type="ip_address",
                        start=match.start(),
                        end=match.end(),
                        matched_text=match.group()
                    ))

        if self.mask_iban:
            seen_iban_starts: set = set()
            for pattern in (self.IBAN_FORMATTED_PATTERN, self.IBAN_COMPACT_PATTERN):
                for match in pattern.finditer(text):
                    if match.start() in seen_iban_starts:
                        continue
                    if self._validate_iban(match.group()):
                        seen_iban_starts.add(match.start())
                        matches.append(PIIMatch(
                            pii_type="iban",
                            start=match.start(),
                            end=match.end(),
                            matched_text=match.group()
                        ))

        if self.mask_eu_vat:
            for match in self.EU_VAT_PATTERN.finditer(text):
                matches.append(PIIMatch(
                    pii_type="eu_vat",
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group()
                ))

        if self.mask_eu_phone:
            for match in self.EU_LOCAL_PHONE_PATTERN.finditer(text):
                matches.append(PIIMatch(
                    pii_type="eu_phone",
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group()
                ))

        # Custom detectors (registered via register_detector)
        for detector in self._custom_detectors:
            try:
                matches.extend(detector.detect(text))
            except Exception:  # nosec B110 - intentional: bad detector must not crash pipeline
                pass

        return sorted(matches, key=lambda x: x.start)

    def mask(self, text: str) -> Tuple[str, List[PIIMatch]]:
        """
        Mask all PII in text.

        Args:
            text: Input text string

        Returns:
            Tuple of (masked_text, list_of_matches)
        """
        matches = self.detect_pii(text)

        if not matches:
            return text, []

        # Build masked text by replacing matches in reverse order
        masked_text = text
        for match in reversed(matches):
            masked_text = (
                masked_text[:match.start] +
                self.replacement_token +
                masked_text[match.end:]
            )

        return masked_text, matches

    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.

        Args:
            text: Input text string

        Returns:
            True if PII detected, False otherwise
        """
        return len(self.detect_pii(text)) > 0

    def get_pii_counts(self, text: str) -> Dict[str, int]:
        """
        Get count of each PII type found in text.

        Args:
            text: Input text string

        Returns:
            Dictionary mapping PII type to count
        """
        matches = self.detect_pii(text)
        counts: Dict[str, int] = {}

        for match in matches:
            counts[match.pii_type] = counts.get(match.pii_type, 0) + 1

        return counts

    @staticmethod
    def _validate_luhn(card_number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm.

        Args:
            card_number: Credit card number string

        Returns:
            True if valid, False otherwise
        """
        # Remove non-digits
        digits = [int(d) for d in card_number if d.isdigit()]

        if len(digits) < 13 or len(digits) > 19:
            return False

        # Luhn algorithm
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    @staticmethod
    def _validate_iban(iban: str) -> bool:
        """Validate IBAN using ISO 13616 mod-97 checksum."""
        iban = re.sub(r'\s', '', iban).upper()
        if len(iban) < 15 or len(iban) > 34:
            return False
        # Move first 4 chars to end, then convert letters to digits (A=10…Z=35)
        rearranged = iban[4:] + iban[:4]
        numeric = ''.join(
            str(ord(c) - ord('A') + 10) if c.isalpha() else c
            for c in rearranged
        )
        try:
            return int(numeric) % 97 == 1
        except ValueError:
            return False

    @staticmethod
    def _validate_ip(ip_address: str) -> bool:
        """
        Validate IP address format.

        Args:
            ip_address: IP address string

        Returns:
            True if valid IP, False otherwise
        """
        parts = ip_address.split('.')
        if len(parts) != 4:
            return False

        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False


def mask_pii(
    text: str,
    mask_emails: bool = True,
    mask_phones: bool = True,
    mask_credit_cards: bool = True,
    mask_ssn: bool = True,
    replacement_token: str = "[REDACTED]"  # nosec B107 - masking token, not a password
) -> Tuple[str, List[PIIMatch]]:
    """
    Convenience function to mask PII in text.

    Args:
        text: Input text string
        mask_emails: Mask email addresses
        mask_phones: Mask phone numbers
        mask_credit_cards: Mask credit card numbers
        mask_ssn: Mask Social Security Numbers
        replacement_token: Token to use for masked PII

    Returns:
        Tuple of (masked_text, list_of_matches)
    """
    masker = PIIMasker(
        mask_emails=mask_emails,
        mask_phones=mask_phones,
        mask_credit_cards=mask_credit_cards,
        mask_ssn=mask_ssn,
        replacement_token=replacement_token
    )
    return masker.mask(text)
