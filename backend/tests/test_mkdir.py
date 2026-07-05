from tools.filesystem import make_directory


def test_creates_a_directory(tmp_path):
    path = tmp_path / "new_dir"

    make_directory(str(path))

    assert path.is_dir()


def test_creates_missing_parent_directories(tmp_path):
    path = tmp_path / "a" / "b" / "c"

    make_directory(str(path))

    assert path.is_dir()


def test_is_a_noop_when_directory_already_exists(tmp_path):
    path = tmp_path / "existing"
    path.mkdir()

    make_directory(str(path))

    assert path.is_dir()


def test_returns_none(tmp_path):
    assert make_directory(str(tmp_path / "new_dir")) is None
