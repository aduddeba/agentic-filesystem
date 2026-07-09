import pytest

from tools.documents import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_returns_single_chunk():
    chunks = chunk_text("hello world", chunk_size=200, overlap=40)

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].text == "hello world"


def test_long_text_splits_into_overlapping_chunks():
    words = [f"word{i}" for i in range(500)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=200, overlap=40)

    assert len(chunks) == 3
    assert chunks[0].text.split() == words[0:200]
    assert chunks[1].text.split() == words[160:360]
    assert chunks[2].text.split() == words[320:500]


def test_consecutive_chunks_share_overlap_words():
    words = [f"w{i}" for i in range(300)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=200, overlap=40)

    first_tail = chunks[0].text.split()[-40:]
    second_head = chunks[1].text.split()[:40]
    assert first_tail == second_head


def test_chunk_indices_are_sequential():
    text = " ".join(f"w{i}" for i in range(500))

    chunks = chunk_text(text, chunk_size=200, overlap=40)

    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunk_size_must_exceed_overlap():
    with pytest.raises(ValueError):
        chunk_text("some words here", chunk_size=10, overlap=10)
