"""Local embedding generation using sentence-transformers (100% offline)."""

import numpy as np
from typing import List, Optional, Union
import warnings

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    warnings.warn(
        "sentence-transformers not installed. "
        "Install with: pip install sentence-transformers"
    )


class LocalEmbedder:
    """
    Local embedding generator using sentence-transformers.

    Uses all-MiniLM-L6-v2 model by default (22MB, 384 dimensions).
    100% offline operation after initial model download.
    """

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize local embedder.

        Args:
            model_name: Model identifier (default: all-MiniLM-L6-v2)
            device: Device to run on ('cpu', 'cuda', or None for auto)
            cache_dir: Directory to cache models (default: ~/.cache)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for semantic deduplication. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self.cache_dir = cache_dir

        self._model = None
        self._embedding_dim = None

    def _load_model(self):
        """Lazy load the model on first use."""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.cache_dir
            )
            # Get embedding dimension
            self._embedding_dim = self._model.get_sentence_embedding_dimension()

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension."""
        if self._embedding_dim is None:
            self._load_model()
        return self._embedding_dim

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text string

        Returns:
            Numpy array of shape (embedding_dim,)
        """
        self._load_model()
        embedding = self._model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embedding

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input text strings
            batch_size: Batch size for processing
            show_progress: Show progress bar

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        self._load_model()
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=show_progress
        )
        return embeddings

    def cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1, higher = more similar)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)

        # Clamp to [0, 1] range
        return float(np.clip(similarity, 0.0, 1.0))

    def find_similar(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray,
        threshold: float = 0.9,
        top_k: Optional[int] = None
    ) -> List[tuple]:
        """
        Find similar embeddings in a corpus.

        Args:
            query_embedding: Query embedding vector (1D)
            corpus_embeddings: Corpus embeddings (2D array)
            threshold: Minimum similarity threshold
            top_k: Return only top K results (None = all above threshold)

        Returns:
            List of (index, similarity) tuples, sorted by similarity
        """
        # Calculate similarities
        similarities = self._batch_cosine_similarity(
            query_embedding,
            corpus_embeddings
        )

        # Filter by threshold
        matches = [
            (idx, float(sim))
            for idx, sim in enumerate(similarities)
            if sim >= threshold
        ]

        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        # Return top K if specified
        if top_k is not None:
            matches = matches[:top_k]

        return matches

    def _batch_cosine_similarity(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate cosine similarities between query and corpus (vectorized).

        Args:
            query_embedding: Query vector (1D)
            corpus_embeddings: Corpus vectors (2D)

        Returns:
            Array of similarity scores
        """
        # Normalize query
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

        # Normalize corpus
        corpus_norms = np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)
        corpus_normalized = corpus_embeddings / (corpus_norms + 1e-10)

        # Compute similarities (dot product)
        similarities = np.dot(corpus_normalized, query_norm)

        # Clamp to [0, 1]
        return np.clip(similarities, 0.0, 1.0)


class SemanticDeduplicator:
    """
    Semantic deduplication using local embeddings.

    Detects near-duplicates based on semantic similarity
    rather than exact text matching.
    """

    def __init__(
        self,
        embedder: LocalEmbedder,
        threshold: float = 0.90,
        store_texts: bool = False
    ):
        """
        Initialize semantic deduplicator.

        Args:
            embedder: LocalEmbedder instance
            threshold: Similarity threshold for duplicates (default: 0.90)
            store_texts: Whether to store original texts (for debugging)
        """
        self.embedder = embedder
        self.threshold = threshold
        self.store_texts = store_texts

        self.embeddings: List[np.ndarray] = []
        self.texts: List[str] = [] if store_texts else None

    def add(self, text: str) -> tuple:
        """
        Add text and check for semantic duplicates.

        Args:
            text: Input text string

        Returns:
            Tuple of (is_unique, similar_index, similarity_score)
            - is_unique: True if no similar text found
            - similar_index: Index of similar text (None if unique)
            - similarity_score: Highest similarity found (None if unique)
        """
        # Generate embedding
        embedding = self.embedder.embed(text)

        # Check against existing embeddings
        if len(self.embeddings) > 0:
            corpus = np.array(self.embeddings)
            matches = self.embedder.find_similar(
                embedding,
                corpus,
                threshold=self.threshold,
                top_k=1
            )

            if matches:
                idx, similarity = matches[0]
                return False, idx, similarity

        # No match found, add to corpus
        self.embeddings.append(embedding)
        if self.store_texts:
            self.texts.append(text)

        return True, None, None

    def reset(self):
        """Clear all stored embeddings."""
        self.embeddings.clear()
        if self.texts is not None:
            self.texts.clear()

    def get_corpus_size(self) -> int:
        """Get number of embeddings stored."""
        return len(self.embeddings)
