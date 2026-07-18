import importlib
import shutil

import pytest

from tools.filesystem import SearchMatch, search

# tools/filesystem/__init__.py does `from .search import search`, which
# rebinds the `search` attribute on the package to the function and shadows
# the submodule. Fetch the submodule via sys.modules (importlib) instead of
# `import tools.filesystem.search`, which would resolve to that same
# shadowed (function) attribute.
search_module = importlib.import_module("tools.filesystem.search")


@pytest.fixture(params=["python", "ripgrep"])
def force_backend(request, monkeypatch):
    """Run a test body against both the python-fallback and ripgrep backends."""
    if request.param == "python":
        monkeypatch.setattr(search_module.shutil, "which", lambda _: None)
    else:
        if shutil.which("rg") is None:
            pytest.skip("ripgrep not installed")
    return request.param


def _by_file_line(matches):
    return {(m.file, m.line): m.text for m in matches}


def test_finds_match_in_single_file(tmp_path, force_backend):
    path = tmp_path / "a.txt"
    path.write_text("first line\nneedle here\nlast line", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert len(matches) == 1
    assert matches[0].line == 2
    assert "needle here" in matches[0].text


def test_no_matches_returns_empty_list(tmp_path, force_backend):
    path = tmp_path / "a.txt"
    path.write_text("nothing relevant here", encoding="utf-8")

    assert search("needle", str(tmp_path)) == []


def test_python_fallback_is_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(search_module.shutil, "which", lambda _: None)
    path = tmp_path / "a.txt"
    path.write_text("Needle in a haystack", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert len(matches) == 1


def test_ripgrep_backend_is_case_sensitive(tmp_path):
    # NOTE: this documents a real discrepancy in search.py: the ripgrep
    # branch does not pass -i/--ignore-case, so unlike the python fallback
    # (which lowercases both sides) it will not match "needle" against
    # "Needle". search() therefore returns different results for the same
    # query depending solely on whether ripgrep happens to be installed.
    if shutil.which("rg") is None:
        pytest.skip("ripgrep not installed")
    path = tmp_path / "a.txt"
    path.write_text("Needle in a haystack", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert matches == []


def test_finds_matches_across_multiple_files(tmp_path, force_backend):
    (tmp_path / "a.txt").write_text("needle in a\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("no match\nneedle again\n", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert len(matches) == 2
    lines = _by_file_line(matches)
    assert (str(tmp_path / "b.txt"), 2) in lines or any(
        m.line == 2 and m.file.endswith("b.txt") for m in matches
    )


def test_finds_multiple_matches_in_same_file(tmp_path, force_backend):
    path = tmp_path / "a.txt"
    path.write_text("needle one\nno match\nneedle two\n", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert sorted(m.line for m in matches) == [1, 3]


def test_searches_nested_subdirectories(tmp_path, force_backend):
    nested = tmp_path / "sub" / "dir"
    nested.mkdir(parents=True)
    (nested / "deep.txt").write_text("needle deep inside\n", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert len(matches) == 1
    assert matches[0].file.endswith("deep.txt")


def test_search_match_is_dataclass_with_expected_fields():
    match = SearchMatch(file="a.txt", line=3, text="some text")

    assert match.file == "a.txt"
    assert match.line == 3
    assert match.text == "some text"


def test_python_fallback_skips_undecodable_files(tmp_path, monkeypatch):
    monkeypatch.setattr(search_module.shutil, "which", lambda _: None)
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02needle\x03")
    (tmp_path / "text.txt").write_text("needle in text\n", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert any(m.file.endswith("text.txt") for m in matches)


def test_uses_ripgrep_when_available(tmp_path, monkeypatch):
    if shutil.which("rg") is None:
        pytest.skip("ripgrep not installed")

    calls = []
    real_which = shutil.which

    def spy_which(name):
        calls.append(name)
        return real_which(name)

    monkeypatch.setattr(search_module.shutil, "which", spy_which)
    (tmp_path / "a.txt").write_text("needle here\n", encoding="utf-8")

    search("needle", str(tmp_path))

    assert "rg" in calls


def test_matches_filename_even_without_content_hit(tmp_path, force_backend):
    (tmp_path / "README.md").write_text("# Agentic AI File System\n\nOverview.", encoding="utf-8")
    (tmp_path / "other.txt").write_text("unrelated content", encoding="utf-8")

    matches = search("README", str(tmp_path))

    assert any(m.file.endswith("README.md") for m in matches)


def test_filename_match_is_case_insensitive(tmp_path, force_backend):
    (tmp_path / "README.md").write_text("nothing relevant", encoding="utf-8")

    matches = search("readme", str(tmp_path))

    assert any(m.file.endswith("README.md") for m in matches)


def test_filename_match_not_duplicated_when_content_also_matches(tmp_path, force_backend):
    (tmp_path / "needle.txt").write_text("needle in a haystack\n", encoding="utf-8")

    matches = search("needle", str(tmp_path))

    assert len(matches) == 1
    assert matches[0].line == 1
    assert "needle in a haystack" in matches[0].text


def test_python_fallback_used_when_ripgrep_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(search_module.shutil, "which", lambda _: None)
    called = {"ripgrep": False}
    monkeypatch.setattr(
        search_module,
        "_search_ripgrep",
        lambda *a, **k: called.update(ripgrep=True) or [],
    )
    (tmp_path / "a.txt").write_text("needle\n", encoding="utf-8")

    search("needle", str(tmp_path))

    assert called["ripgrep"] is False
