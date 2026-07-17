"""Implementation behind the Embedding MCP server -- wraps `tools/embeddings/*`
(sentence-transformers, BAAI/bge-small-en-v1.5, loaded once and kept warm)."""

from typing import TypedDict

from tools.embeddings import embed_passages, embed_query


class GenerateOut(TypedDict):
    embeddings: list[list[float]]


def generate(texts: list[str]) -> GenerateOut:
    """Embed a batch of passage/document texts."""
    return GenerateOut(embeddings=embed_passages(texts))


class QueryOut(TypedDict):
    embedding: list[float]


def query(text: str) -> QueryOut:
    """Embed a search query, applying BGE's asymmetric retrieval instruction prefix."""
    return QueryOut(embedding=embed_query(text))
