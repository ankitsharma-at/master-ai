"""Tool embedding - lightweight hash-based implementation."""
import hashlib
import numpy as np
from typing import List
from core.config import get_settings


def embed(text: str) -> List[float]:
    """Generate a deterministic embedding for text using hash-based approach.

    This is a lightweight replacement for sentence-transformers that works
    without PyTorch/Windows DLL issues. Uses cryptographic hashes and
    word distribution to create semantic-like embeddings.

    Args:
        text: Input text to embed

    Returns:
        384-dimensional embedding vector (normalized)
    """
    settings = get_settings()

    # Normalize text
    text_lower = text.lower().strip()
    words = text_lower.split()

    # Create 384-dimensional embedding (same size as all-MiniLM-L6-v2)
    embedding = np.zeros(384, dtype=np.float32)

    # Word-based features
    for i, word in enumerate(words[:100]):  # Limit to first 100 words
        word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
        # Distribute word across multiple dimensions
        for j in range(4):
            dim = (word_hash + j * 96) % 384
            embedding[dim] += 1.0 / (i + 1)  # Diminishing weight by position

    # Text-level features for overall semantics
    text_hash = int(hashlib.sha256(text_lower.encode()).hexdigest(), 16)
    for i in range(10):
        dim = (text_hash + i) % 384
        embedding[dim] += 0.5

    # Character n-gram features (captures partial word similarities)
    for i in range(len(text_lower) - 2):
        trigram = text_lower[i:i+3]
        ngram_hash = int(hashlib.md5(trigram.encode()).hexdigest(), 16)
        dim = ngram_hash % 384
        embedding[dim] += 0.1

    # Length feature (normalized)
    length_feature = min(len(text) / 1000, 1.0)
    embedding[383] = length_feature

    # Normalize to unit length (important for cosine similarity)
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding.tolist()
