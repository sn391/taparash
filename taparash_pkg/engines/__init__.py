"""Local ML engines for Taparash (100% offline)."""

try:
    from .embeddings import LocalEmbedder, SemanticDeduplicator
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    LocalEmbedder = None
    SemanticDeduplicator = None
    EMBEDDINGS_AVAILABLE = False

try:
    from .nli import LocalNLI, ContradictionDetector, CoherenceValidator
    NLI_AVAILABLE = True
except ImportError:
    LocalNLI = None
    ContradictionDetector = None
    CoherenceValidator = None
    NLI_AVAILABLE = False

__all__ = [
    "LocalEmbedder",
    "SemanticDeduplicator",
    "LocalNLI",
    "ContradictionDetector",
    "CoherenceValidator",
]
