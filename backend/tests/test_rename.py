import pytest

from tools.filesystem import rename


def test_renames_a_file(tmp_path):
    src = tmp_path / "old.txt"
    src.write_text("hello", encoding="utf-8")
    dst = tmp_path / "new.txt"

    rename(str(src), str(dst))

    assert not src.exists()
    assert dst.read_text(encoding="utf-8") == "hello"


def test_renames_a_directory(tmp_path):
    src = tmp_path / "old_dir"
    src.mkdir()
    (src / "note.txt").write_text("hello", encoding="utf-8")
    dst = tmp_path / "new_dir"

    rename(str(src), str(dst))

    assert not src.exists()
    assert (dst / "note.txt").read_text(encoding="utf-8") == "hello"


def test_creates_missing_destination_parents(tmp_path):
    src = tmp_path / "old.txt"
    src.write_text("hello", encoding="utf-8")
    dst = tmp_path / "nested" / "dir" / "new.txt"

    rename(str(src), str(dst))

    assert dst.read_text(encoding="utf-8") == "hello"


def test_missing_source_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        rename(str(tmp_path / "missing.txt"), str(tmp_path / "new.txt"))


def test_existing_destination_raises_file_exists(tmp_path):
    src = tmp_path / "old.txt"
    src.write_text("hello", encoding="utf-8")
    dst = tmp_path / "new.txt"
    dst.write_text("already here", encoding="utf-8")

    with pytest.raises(FileExistsError):
        rename(str(src), str(dst))
