"""Deduplication utilities for text using exact and fuzzy matching."""

import hashlib
import re
from typing import List, Set, Tuple, Optional
from collections import defaultdict


def sha256_hash(text: str) -> str:
    """
    Calculate SHA256 hash of text for exact deduplication.

    Args:
        text: Input text string

    Returns:
        Hexadecimal SHA256 hash string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class ExactDeduplicator:
    """Exact deduplication using SHA256 hashing."""

    def __init__(self):
        """Initialize deduplicator with empty hash set."""
        self.seen_hashes: Set[str] = set()
        self.hash_to_indices: defaultdict = defaultdict(list)

    def add(self, text: str, index: Optional[int] = None) -> bool:
        """
        Add text and check if it's a duplicate.

        Args:
            text: Input text string
            index: Optional index to track which items are duplicates

        Returns:
            True if text is new (not a duplicate), False if duplicate
        """
        text_hash = sha256_hash(text)

        if index is not None:
            self.hash_to_indices[text_hash].append(index)

        if text_hash in self.seen_hashes:
            return False

        self.seen_hashes.add(text_hash)
        return True

    def is_duplicate(self, text: str) -> bool:
        """
        Check if text is a duplicate without adding it.

        Args:
            text: Input text string

        Returns:
            True if text is a duplicate, False otherwise
        """
        text_hash = sha256_hash(text)
        return text_hash in self.seen_hashes

    def get_duplicate_groups(self) -> List[List[int]]:
        """
        Get groups of duplicate indices.

        Returns:
            List of lists, where each inner list contains indices of duplicates
        """
        return [indices for indices in self.hash_to_indices.values() if len(indices) > 1]

    def reset(self):
        """Clear all stored hashes."""
        self.seen_hashes.clear()
        self.hash_to_indices.clear()


def create_shingles(text: str, k: int = 3) -> Set[str]:
    """
    Create k-shingles (character n-grams) from text.

    Args:
        text: Input text string
        k: Shingle size (default: 3)

    Returns:
        Set of k-character shingles
    """
    if len(text) < k:
        return {text}

    return {text[i:i+k] for i in range(len(text) - k + 1)}


def create_word_shingles(text: str, k: int = 3) -> Set[str]:
    """
    Create k-shingles (word n-grams) from text.

    Args:
        text: Input text string
        k: Shingle size in words (default: 3)

    Returns:
        Set of k-word shingles
    """
    words = re.findall(r'\w+', text.lower())

    if len(words) < k:
        return {' '.join(words)}

    return {' '.join(words[i:i+k]) for i in range(len(words) - k + 1)}


class MinHashDeduplicator:
    """Fuzzy deduplication using MinHash locality-sensitive hashing."""

    def __init__(self, num_perm: int = 128, threshold: float = 0.8,
                 shingle_size: int = 3, use_word_shingles: bool = False,
                 seed: int = 42):
        """
        Initialize MinHash deduplicator.

        Args:
            num_perm: Number of hash permutations (default: 128)
            threshold: Jaccard similarity threshold for duplicates (default: 0.8)
            shingle_size: Size of shingles (default: 3)
            use_word_shingles: Use word-based shingles instead of character-based
            seed: Random seed for deterministic hash functions (default: 42)
        """
        self.num_perm = num_perm
        self.threshold = threshold
        self.shingle_size = shingle_size
        self.use_word_shingles = use_word_shingles

        # Generate deterministic hash coefficients for permutations
        import random
        rng = random.Random(seed)
        self.hash_params = [
            (rng.randint(1, 2**32 - 1), rng.randint(1, 2**32 - 1))
            for _ in range(num_perm)
        ]

        self.signatures: List[List[int]] = []
        self.texts: List[str] = []

    def _hash_shingle(self, shingle: str, a: int, b: int) -> int:
        """
        Hash a shingle with permutation parameters.

        Args:
            shingle: Shingle string
            a: First hash parameter
            b: Second hash parameter

        Returns:
            Hash value
        """
        base_hash = int(hashlib.sha256(shingle.encode('utf-8')).hexdigest(), 16)
        return (a * base_hash + b) % (2**32 - 1)

    def _create_signature(self, text: str) -> List[int]:
        """
        Create MinHash signature for text.

        Args:
            text: Input text string

        Returns:
            MinHash signature as list of integers
        """
        # Create shingles
        if self.use_word_shingles:
            shingles = create_word_shingles(text, self.shingle_size)
        else:
            shingles = create_shingles(text, self.shingle_size)

        if not shingles:
            return [2**32 - 1] * self.num_perm

        # Initialize signature with maximum values
        signature = [2**32 - 1] * self.num_perm

        # Calculate MinHash signature
        for shingle in shingles:
            for i, (a, b) in enumerate(self.hash_params):
                hash_value = self._hash_shingle(shingle, a, b)
                signature[i] = min(signature[i], hash_value)

        return signature

    def add(self, text: str) -> Tuple[bool, Optional[int]]:
        """
        Add text and check if it's similar to existing texts.

        Args:
            text: Input text string

        Returns:
            Tuple of (is_unique, duplicate_index)
            - is_unique: True if text is unique, False if similar to existing
            - duplicate_index: Index of similar text if found, None otherwise
        """
        signature = self._create_signature(text)

        # Check against existing signatures
        for idx, existing_sig in enumerate(self.signatures):
            similarity = self._estimate_jaccard(signature, existing_sig)
            if similarity >= self.threshold:
                return False, idx

        # Add new signature
        self.signatures.append(signature)
        self.texts.append(text)
        return True, None

    def _estimate_jaccard(self, sig1: List[int], sig2: List[int]) -> float:
        """
        Estimate Jaccard similarity from MinHash signatures.

        Args:
            sig1: First MinHash signature
            sig2: Second MinHash signature

        Returns:
            Estimated Jaccard similarity (0-1)
        """
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have same length")

        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)

    def find_similar(self, text: str) -> List[Tuple[int, float]]:
        """
        Find all texts similar to the input text.

        Args:
            text: Input text string

        Returns:
            List of tuples (index, similarity) for texts above threshold
        """
        signature = self._create_signature(text)
        results = []

        for idx, existing_sig in enumerate(self.signatures):
            similarity = self._estimate_jaccard(signature, existing_sig)
            if similarity >= self.threshold:
                results.append((idx, similarity))

        return results

    def reset(self):
        """Clear all stored signatures and texts."""
        self.signatures.clear()
        self.texts.clear()


def deduplicate_exact(texts: List[str]) -> Tuple[List[str], List[int]]:
    """
    Remove exact duplicates from a list of texts.

    Args:
        texts: List of text strings

    Returns:
        Tuple of (unique_texts, kept_indices)
        - unique_texts: List of unique texts
        - kept_indices: Indices of kept texts from original list
    """
    deduplicator = ExactDeduplicator()
    unique_texts = []
    kept_indices = []

    for idx, text in enumerate(texts):
        if deduplicator.add(text, idx):
            unique_texts.append(text)
            kept_indices.append(idx)

    return unique_texts, kept_indices


def deduplicate_fuzzy(texts: List[str], threshold: float = 0.8,
                     num_perm: int = 128, shingle_size: int = 3,
                     use_word_shingles: bool = False, seed: int = 42) -> Tuple[List[str], List[int]]:
    """
    Remove fuzzy duplicates from a list of texts using MinHash.

    Args:
        texts: List of text strings
        threshold: Jaccard similarity threshold (default: 0.8)
        num_perm: Number of hash permutations (default: 128)
        shingle_size: Size of shingles (default: 3)
        use_word_shingles: Use word-based shingles instead of character-based
        seed: Random seed for deterministic hashing (default: 42)

    Returns:
        Tuple of (unique_texts, kept_indices)
        - unique_texts: List of unique texts
        - kept_indices: Indices of kept texts from original list
    """
    deduplicator = MinHashDeduplicator(
        num_perm=num_perm,
        threshold=threshold,
        shingle_size=shingle_size,
        use_word_shingles=use_word_shingles,
        seed=seed
    )

    unique_texts = []
    kept_indices = []

    for idx, text in enumerate(texts):
        is_unique, _ = deduplicator.add(text)
        if is_unique:
            unique_texts.append(text)
            kept_indices.append(idx)

    return unique_texts, kept_indices
