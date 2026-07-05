import pytest

from tools.filesystem import delete


def test_deletes_a_file(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("hello", encoding="utf-8")

    delete(str(path))

    assert not path.exists()


def test_deletes_a_directory_recursively(tmp_path):
    nested = tmp_path / "dir" / "sub"
    nested.mkdir(parents=True)
    (nested / "note.txt").write_text("hello", encoding="utf-8")

    delete(str(tmp_path / "dir"))

    assert not (tmp_path / "dir").exists()


def test_missing_path_raises_file_not_found(tmp_path):
    missing = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        delete(str(missing))


def test_returns_none(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("hello", encoding="utf-8")

    assert delete(str(path)) is None
