"""PII detection and masking using regex patterns."""

import re
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class PIIMatch:
    """Represents a detected PII match."""

    pii_type: str
    start: int
    end: int
    matched_text: str


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

    def __init__(
        self,
        mask_emails: bool = True,
        mask_phones: bool = True,
        mask_credit_cards: bool = True,
        mask_ssn: bool = True,
        mask_ip_addresses: bool = False,
        replacement_token: str = "[REDACTED]"
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
        self.replacement_token = replacement_token

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
    replacement_token: str = "[REDACTED]"
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
