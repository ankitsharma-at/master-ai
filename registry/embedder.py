"""Embedding pipeline using sentence-transformers."""
import numpy as np
from sentence_transformers import SentenceTransformer
import structlog
from core.config import get_settings

log = structlog.get_logger()


class ToolEmbedder:
    def __init__(self):
        settings = get_settings()
        self.model = SentenceTransformer(settings.embedding_model)
        self.dim = self.model.get_sentence_embedding_dimension()
        log.info("embedder.initialized", model=settings.embedding_model, dim=self.dim)

    def embed(self, text: str) -> list[float]:
        """Convert text to embedding vector."""
        if not text or not isinstance(text, str):
            return [0.0] * self.dim
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Convert multiple texts to embedding vectors."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
