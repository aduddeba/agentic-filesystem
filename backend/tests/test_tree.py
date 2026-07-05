from tools.filesystem import walk


def test_empty_directory_returns_empty_list(tmp_path):
    assert walk(str(tmp_path)) == []


def test_missing_root_returns_empty_list(tmp_path):
    assert walk(str(tmp_path / "missing")) == []


def test_lists_files_at_root(tmp_path):
    (tmp_path / "b.txt").write_text("hi", encoding="utf-8")
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")

    entries = walk(str(tmp_path))

    assert [e.name for e in entries] == ["a.txt", "b.txt"]
    assert all(e.depth == 0 and not e.is_dir for e in entries)


def test_folders_are_listed_before_files(tmp_path):
    (tmp_path / "z_file.txt").write_text("hi", encoding="utf-8")
    (tmp_path / "a_dir").mkdir()

    entries = walk(str(tmp_path))

    assert [e.name for e in entries] == ["a_dir", "z_file.txt"]
    assert entries[0].is_dir
    assert not entries[1].is_dir


def test_nested_entries_get_increasing_depth(tmp_path):
    nested = tmp_path / "dir" / "sub"
    nested.mkdir(parents=True)
    (nested / "note.txt").write_text("hi", encoding="utf-8")

    entries = walk(str(tmp_path))
    by_name = {e.name: e for e in entries}

    assert by_name["dir"].depth == 0
    assert by_name["sub"].depth == 1
    assert by_name["note.txt"].depth == 2


def test_paths_are_relative_posix_from_root(tmp_path):
    nested = tmp_path / "dir"
    nested.mkdir()
    (nested / "note.txt").write_text("hi", encoding="utf-8")

    entries = walk(str(tmp_path))
    by_name = {e.name: e for e in entries}

    assert by_name["dir"].path == "dir"
    assert by_name["note.txt"].path == "dir/note.txt"


def test_file_size_is_reported_and_directory_size_is_zero(tmp_path):
    (tmp_path / "note.txt").write_text("hello world", encoding="utf-8")
    (tmp_path / "empty_dir").mkdir()

    entries = walk(str(tmp_path))
    by_name = {e.name: e for e in entries}

    assert by_name["note.txt"].size == len("hello world")
    assert by_name["empty_dir"].size == 0


def test_sorting_is_case_insensitive(tmp_path):
    (tmp_path / "Banana.txt").write_text("hi", encoding="utf-8")
    (tmp_path / "apple.txt").write_text("hi", encoding="utf-8")

    entries = walk(str(tmp_path))

    assert [e.name for e in entries] == ["apple.txt", "Banana.txt"]
