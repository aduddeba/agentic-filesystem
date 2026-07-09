from tools.filesystem import write

def test_writes_content_to_new_file(tmp_path):
    path = tmp_path / "note.txt"

    write(str(path), "hello world")

    assert path.read_text(encoding="utf-8") == "hello world"


def test_returns_none(tmp_path):
    path = tmp_path / "note.txt"

    assert write(str(path), "content") is None


def test_creates_missing_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dirs" / "note.txt"

    write(str(path), "deep content")

    assert path.read_text(encoding="utf-8") == "deep content"


def test_overwrites_existing_file(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("old content", encoding="utf-8")

    write(str(path), "new content")

    assert path.read_text(encoding="utf-8") == "new content"


def test_writes_non_ascii_utf8_content(tmp_path):
    path = tmp_path / "note.txt"

    write(str(path), "café ☃")

    assert path.read_text(encoding="utf-8") == "café ☃"


def test_writes_empty_content(tmp_path):
    path = tmp_path / "note.txt"

    write(str(path), "")

    assert path.read_text(encoding="utf-8") == ""


def test_existing_parent_directory_is_left_untouched(tmp_path):
    parent = tmp_path / "existing"
    parent.mkdir()
    sibling = parent / "sibling.txt"
    sibling.write_text("sibling", encoding="utf-8")
    path = parent / "note.txt"

    write(str(path), "content")

    assert sibling.read_text(encoding="utf-8") == "sibling"
