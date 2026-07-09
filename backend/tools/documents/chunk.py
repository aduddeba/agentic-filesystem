"""Split text into overlapping word-based chunks for embedding."""

from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    text: str


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> list[Chunk]:
    """Split `text` into overlapping chunks of `chunk_size` words.

    Consecutive chunks share `overlap` words so passages that straddle a
    boundary still appear whole in at least one chunk. Returns an empty
    list for blank/whitespace-only text.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    words = text.split()
    if not words:
        return []

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    index = 0
    start = 0
    while True:
        piece = words[start : start + chunk_size]
        chunks.append(Chunk(index=index, text=" ".join(piece)))
        if start + chunk_size >= len(words):
            break
        start += step
        index += 1
    return chunks
