"""
Embedding Service

Generates semantic embeddings for text using sentence-transformers.
Used for similarity matching between resumes and jobs.

Phase 4 implementation per PROJECT_PLAN.md.

Dependencies:
- sentence-transformers: Embedding generation
- numpy: Array operations
"""

import logging
from typing import List, Union
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generate semantic embeddings for text.

    Uses sentence-transformers (all-MiniLM-L6-v2) for 384-dim embeddings.
    Singleton pattern to avoid loading model multiple times.

    Full implementation in Phase 4.
    """

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Model loaded lazily on first use
        pass

    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                from django.conf import settings
                model_name = getattr(settings, 'EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
                self._model = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}")
            except ImportError:
                logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
                raise

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            numpy array of shape (384,)

        Full implementation in Phase 4.
        """
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)

        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)

    def generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently.

        Full implementation in Phase 4.
        """
        self._load_model()
        texts = [t if t else '' for t in texts]
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.astype(np.float32)

    @staticmethod
    def serialize_embedding(embedding: np.ndarray) -> bytes:
        """Convert embedding to bytes for database storage."""
        return embedding.astype(np.float32).tobytes()

    @staticmethod
    def deserialize_embedding(data: bytes) -> np.ndarray:
        """Convert bytes back to embedding array."""
        return np.frombuffer(data, dtype=np.float32)
