"""Shannon entropy calculation for text analysis."""

import math
from collections import Counter


def shannon_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of a text string.

    Shannon entropy measures the randomness/information content of text.
    Higher values indicate more random/unpredictable text.

    Args:
        text: Input text string

    Returns:
        Shannon entropy value in bits per character
    """
    if not text:
        return 0.0

    # Count character frequencies
    char_counts = Counter(text)
    text_length = len(text)

    # Calculate entropy: H(X) = -Σ p(x) * log2(p(x))
    entropy = 0.0
    for count in char_counts.values():
        probability = count / text_length
        entropy -= probability * math.log2(probability)

    return entropy


def is_gibberish(text: str, threshold: float = 4.2) -> bool:
    """
    Determine if text is likely gibberish based on Shannon entropy.

    Natural language typically has entropy between 3.5-4.5 bits per character.
    Values significantly above this threshold suggest random or encrypted text.

    Args:
        text: Input text string
        threshold: Entropy threshold above which text is considered gibberish
                  (default: 4.2)

    Returns:
        True if text entropy exceeds threshold, False otherwise
    """
    if not text:
        return False

    entropy = shannon_entropy(text)
    return entropy > threshold
