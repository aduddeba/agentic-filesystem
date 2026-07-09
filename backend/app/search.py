"""Semantic and hybrid (keyword + vector) search over indexed file chunks."""

from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from tools.embeddings import embed_query
from tools.filesystem import search as keyword_search_tool

from .config import settings
from .models import Chunk, FileRecord
from .paths import to_relative
from .schemas import SemanticMatchOut

# Reciprocal rank fusion constant -- large-ish so that a single low-ranked
# appearance in one list doesn't dominate a high rank in the other.
_RRF_K = 60

# How many raw chunk hits to pull before de-duplicating down to distinct
# files, so a query where the top hits cluster in one file still surfaces k
# distinct files.
_OVERFETCH_FACTOR = 3


def vector_search(db: Session, query_vector: list[float], k: int) -> list[tuple[FileRecord, Chunk, float]]:
    """Return the k nearest chunks to `query_vector` as (file, chunk, cosine distance) tuples."""
    distance = Chunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(FileRecord, Chunk, distance.label("distance"))
        .join(Chunk, Chunk.file_id == FileRecord.id)
        .order_by(distance)
        .limit(k)
    )
    return [(record, chunk, distance) for record, chunk, distance in db.execute(stmt).all()]


def semantic_search(
    db: Session, query: str, k: int = 10, mode: Literal["hybrid", "vector"] = "hybrid"
) -> list[SemanticMatchOut]:
    """Search indexed file chunks for `query`, ranked by embedding similarity.

    In "hybrid" mode, results are fused with the existing ripgrep-based
    keyword search via reciprocal rank fusion, so exact-term matches still
    surface even when their embedding similarity is mediocre.
    """
    query_vector = embed_query(query)
    vector_hits = vector_search(db, query_vector, k=k * _OVERFETCH_FACTOR)

    if mode == "vector":
        return _dedupe_by_path(vector_hits, k)

    return _hybrid_fuse(vector_hits, query, k)


def _dedupe_by_path(vector_hits: list[tuple[FileRecord, Chunk, float]], k: int) -> list[SemanticMatchOut]:
    results: list[SemanticMatchOut] = []
    seen: set[str] = set()
    for record, chunk, distance in vector_hits:
        if record.path in seen:
            continue
        seen.add(record.path)
        results.append(SemanticMatchOut(path=record.path, text=chunk.text, score=1 - distance))
        if len(results) >= k:
            break
    return results


def _hybrid_fuse(vector_hits: list[tuple[FileRecord, Chunk, float]], query: str, k: int) -> list[SemanticMatchOut]:
    vector_rank: dict[str, tuple[int, str]] = {}
    for rank, (record, chunk, _distance) in enumerate(vector_hits):
        if record.path not in vector_rank:
            vector_rank[record.path] = (rank, chunk.text)

    keyword_rank: dict[str, tuple[int, str]] = {}
    for rank, match in enumerate(keyword_search_tool(query, root=settings.storage_root)):
        path = to_relative(Path(match.file))
        if path not in keyword_rank:
            keyword_rank[path] = (rank, match.text)

    fused: dict[str, float] = {}
    for path, (rank, _snippet) in vector_rank.items():
        fused[path] = fused.get(path, 0.0) + 1 / (_RRF_K + rank + 1)
    for path, (rank, _snippet) in keyword_rank.items():
        fused[path] = fused.get(path, 0.0) + 1 / (_RRF_K + rank + 1)

    ranked_paths = sorted(fused, key=lambda p: fused[p], reverse=True)[:k]
    return [
        SemanticMatchOut(
            path=path,
            text=vector_rank[path][1] if path in vector_rank else keyword_rank[path][1],
            score=fused[path],
        )
        for path in ranked_paths
    ]
