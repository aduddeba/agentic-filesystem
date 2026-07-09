"""Generate sentence embeddings for text via a local sentence-transformers model."""

from functools import lru_cache

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384

# BGE is an asymmetric retrieval model: queries need this instruction prefix to
# align with unprefixed passage embeddings. See the model card on HuggingFace.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed a batch of passage/document texts."""
    if not texts:
        return []
    vectors = _model().encode(list(texts), normalize_embeddings=True)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a search query, applying BGE's retrieval instruction prefix."""
    vectors = _model().encode([_QUERY_PREFIX + text], normalize_embeddings=True)
    return vectors[0].tolist()
