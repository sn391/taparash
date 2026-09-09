"""Local Natural Language Inference (NLI) for contradiction detection."""

import numpy as np
from typing import List, Optional, Tuple, Dict
import warnings

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    warnings.warn(
        "sentence-transformers not installed. "
        "Install with: pip install sentence-transformers"
    )


class LocalNLI:
    """
    Local NLI model using Cross-Encoder for contradiction detection.

    Uses cross-encoder/nli-deberta-v3-base by default.
    100% offline operation after initial model download.
    """

    DEFAULT_MODEL = "cross-encoder/nli-deberta-v3-base"

    # Label mappings for NLI models
    LABEL_CONTRADICTION = 0
    LABEL_NEUTRAL = 1
    LABEL_ENTAILMENT = 2

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize local NLI model.

        Args:
            model_name: Model identifier (default: nli-deberta-v3-base)
            device: Device to run on ('cpu', 'cuda', or None for auto)
            cache_dir: Directory to cache models (default: ~/.cache)
        """
        if not CROSS_ENCODER_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for NLI. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self.cache_dir = cache_dir

        self._model = None

    def _load_model(self):
        """Lazy load the model on first use."""
        if self._model is None:
            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
                default_activation_function=None  # Get raw logits
            )

    def predict(
        self,
        premise: str,
        hypothesis: str,
        return_logits: bool = False
    ) -> Tuple[int, float, List[float]]:
        """
        Predict NLI relationship between premise and hypothesis.

        Args:
            premise: The premise text
            hypothesis: The hypothesis text
            return_logits: If True, return raw logits instead of probabilities

        Returns:
            Tuple of (label, score, all_scores)
            - label: 0=contradiction, 1=neutral, 2=entailment
            - score: Confidence score for predicted label
            - all_scores: List of scores for all labels
        """
        self._load_model()

        # Get predictions
        scores = self._model.predict(
            [[premise, hypothesis]],
            apply_softmax=not return_logits,
            convert_to_numpy=True
        )[0]

        # Get predicted label and its score
        label = int(np.argmax(scores))
        score = float(scores[label])

        return label, score, scores.tolist()

    def is_contradiction(
        self,
        text1: str,
        text2: str,
        threshold: float = 0.5
    ) -> Tuple[bool, float]:
        """
        Check if two texts contradict each other.

        Args:
            text1: First text
            text2: Second text
            threshold: Minimum confidence for contradiction (default: 0.5)

        Returns:
            Tuple of (is_contradiction, confidence)
        """
        label, score, _ = self.predict(text1, text2)

        is_contradiction = (label == self.LABEL_CONTRADICTION and score >= threshold)
        contradiction_confidence = score if label == self.LABEL_CONTRADICTION else 0.0

        return is_contradiction, contradiction_confidence

    def predict_batch(
        self,
        pairs: List[Tuple[str, str]],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[Tuple[int, float, List[float]]]:
        """
        Predict NLI relationships for multiple text pairs.

        Args:
            pairs: List of (premise, hypothesis) tuples
            batch_size: Batch size for processing
            show_progress: Show progress bar

        Returns:
            List of (label, score, all_scores) tuples
        """
        self._load_model()

        # Get predictions for all pairs
        all_scores = self._model.predict(
            pairs,
            batch_size=batch_size,
            apply_softmax=True,
            convert_to_numpy=True,
            show_progress_bar=show_progress
        )

        results = []
        for scores in all_scores:
            label = int(np.argmax(scores))
            score = float(scores[label])
            results.append((label, score, scores.tolist()))

        return results


class ContradictionDetector:
    """
    Detect contradictions in text corpus using local NLI model.

    Compares new text against stored context to find contradictions.
    """

    def __init__(
        self,
        nli_model: LocalNLI,
        threshold: float = 0.7,
        store_texts: bool = True,
        max_context_size: int = 100
    ):
        """
        Initialize contradiction detector.

        Args:
            nli_model: LocalNLI instance
            threshold: Contradiction confidence threshold (default: 0.7)
            store_texts: Whether to store texts for context (default: True)
            max_context_size: Maximum number of texts to keep in context
        """
        self.nli_model = nli_model
        self.threshold = threshold
        self.store_texts = store_texts
        self.max_context_size = max_context_size

        self.context: List[str] = []

    def add(self, text: str) -> Tuple[bool, Optional[int], Optional[float]]:
        """
        Add text and check for contradictions with existing context.

        Args:
            text: Input text string

        Returns:
            Tuple of (is_valid, contradicting_index, confidence)
            - is_valid: True if no contradiction found
            - contradicting_index: Index of contradicting text (None if valid)
            - confidence: Contradiction confidence score (None if valid)
        """
        if not self.context:
            # First text, no contradiction possible
            if self.store_texts:
                self.context.append(text)
            return True, None, None

        # Check against all texts in context
        for idx, context_text in enumerate(self.context):
            is_contradiction, confidence = self.nli_model.is_contradiction(
                context_text,
                text,
                threshold=self.threshold
            )

            if is_contradiction:
                return False, idx, confidence

        # No contradiction found, add to context
        if self.store_texts:
            self.context.append(text)

            # Maintain max context size (FIFO)
            if len(self.context) > self.max_context_size:
                self.context.pop(0)

        return True, None, None

    def check_batch_internal_contradictions(
        self,
        texts: List[str],
        return_pairs: bool = False
    ) -> List[Dict]:
        """
        Check for contradictions within a batch of texts.

        Args:
            texts: List of texts to check
            return_pairs: If True, return all contradicting pairs

        Returns:
            List of contradiction dictionaries with indices and confidence
        """
        contradictions = []

        # Generate all pairs
        pairs = []
        pair_indices = []

        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                pairs.append((texts[i], texts[j]))
                pair_indices.append((i, j))

        if not pairs:
            return contradictions

        # Batch predict
        results = self.nli_model.predict_batch(pairs)

        # Check for contradictions
        for (i, j), (label, score, _) in zip(pair_indices, results):
            if label == LocalNLI.LABEL_CONTRADICTION and score >= self.threshold:
                contradictions.append({
                    'index1': i,
                    'index2': j,
                    'text1': texts[i] if return_pairs else None,
                    'text2': texts[j] if return_pairs else None,
                    'confidence': score
                })

        return contradictions

    def reset(self):
        """Clear stored context."""
        self.context.clear()

    def get_context_size(self) -> int:
        """Get number of texts in context."""
        return len(self.context)


class CoherenceValidator:
    """
    Validate context coherence using NLI.

    Checks if new text is coherent with existing context
    (not contradicting and ideally entailed or neutral).
    """

    def __init__(
        self,
        nli_model: LocalNLI,
        contradiction_threshold: float = 0.7,
        entailment_threshold: float = 0.5,
        require_entailment: bool = False
    ):
        """
        Initialize coherence validator.

        Args:
            nli_model: LocalNLI instance
            contradiction_threshold: Threshold for contradiction rejection
            entailment_threshold: Threshold for entailment requirement
            require_entailment: If True, require entailment (not just non-contradiction)
        """
        self.nli_model = nli_model
        self.contradiction_threshold = contradiction_threshold
        self.entailment_threshold = entailment_threshold
        self.require_entailment = require_entailment

        self.context: List[str] = []

    def is_coherent(
        self,
        text: str,
        context: Optional[List[str]] = None
    ) -> Tuple[bool, str, float]:
        """
        Check if text is coherent with context.

        Args:
            text: Text to validate
            context: Optional context (uses stored context if None)

        Returns:
            Tuple of (is_coherent, reason, confidence)
        """
        check_context = context if context is not None else self.context

        if not check_context:
            return True, "no_context", 1.0

        # Check against most recent context (last 5 texts)
        recent_context = check_context[-5:]

        for context_text in recent_context:
            label, score, _ = self.nli_model.predict(context_text, text)

            # Check for contradiction
            if label == LocalNLI.LABEL_CONTRADICTION and score >= self.contradiction_threshold:
                return False, "contradiction", score

            # Check for entailment requirement
            if self.require_entailment:
                if label == LocalNLI.LABEL_ENTAILMENT and score >= self.entailment_threshold:
                    return True, "entailed", score

        # If require_entailment and we didn't find entailment
        if self.require_entailment:
            return False, "not_entailed", 0.0

        # No contradiction found (and entailment not required)
        return True, "coherent", 1.0

    def add_to_context(self, text: str):
        """Add text to context for future coherence checks."""
        self.context.append(text)

        # Keep only last 20 texts for efficiency
        if len(self.context) > 20:
            self.context.pop(0)

    def reset(self):
        """Clear context."""
        self.context.clear()
