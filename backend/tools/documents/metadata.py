"""Derive lightweight metadata for a file from its path and extracted text."""

import mimetypes
from dataclasses import dataclass


@dataclass
class Metadata:
    mime_type: str | None
    word_count: int
    char_count: int


def extract_metadata(path: str, text: str) -> Metadata:
    """Guess the MIME type from `path` and count words/characters in `text`."""
    mime_type, _ = mimetypes.guess_type(path)
    return Metadata(
        mime_type=mime_type,
        word_count=len(text.split()),
        char_count=len(text),
    )
