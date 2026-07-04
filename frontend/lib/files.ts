// Escaping a backtick inside a template literal (`\``) is a lexical requirement
// of the delimiter itself, so String.raw preserves the backslash along with
// it -- it would show up as a literal stray backslash in the rendered code.
// Splice real backtick characters in via concatenation instead.
const BT = String.fromCharCode(96);

export const FILES_INITIAL: Record<string, string> = {
  "backend/tools/filesystem/__init__.py": String.raw`from .read import read
from .search import search, SearchMatch
from .write import write`,

  "backend/tools/filesystem/read.py": String.raw`"""Read the text contents of a file, regardless of format."""

from pathlib import Path


def read(file: str) -> str:
    """Read a file and return its contents as plain text.

    Dispatches on file extension: PDFs and Office documents are parsed
    into text, everything else is read as UTF-8.
    """
    path = Path(file)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix in (".xlsx", ".xlsm"):
        return _read_xlsx(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    import fitz  # PyMuPDF

    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def _read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _read_xlsx(path: Path) -> str:
    import openpyxl

    workbook = openpyxl.load_workbook(path, data_only=True)
    lines = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            lines.append("\t".join("" if v is None else str(v) for v in row))
    return "\n".join(lines)`,

  "backend/tools/filesystem/search.py": String.raw`"""Search for a text query across files under a directory."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchMatch:
    file: str
    line: int
    text: str


def search(query: str, root: str = ".") -> list[SearchMatch]:
    """Search for ` + BT + "query" + BT + " across files under " + BT + "root" + BT + String.raw`.

    Uses ripgrep when available for speed; falls back to a pure-Python
    walk otherwise so this works without any external binary installed.
    """
    rg_path = shutil.which("rg")
    if rg_path is not None:
        return _search_ripgrep(rg_path, query, root)
    return _search_python(query, root)


def _search_ripgrep(rg_path: str, query: str, root: str) -> list[SearchMatch]:
    result = subprocess.run(
        [rg_path, "--json", query, root],
        capture_output=True,
        text=True,
    )

    matches = []
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if event.get("type") != "match":
            continue
        data = event["data"]
        matches.append(
            SearchMatch(
                file=data["path"]["text"],
                line=data["line_number"],
                text=data["lines"]["text"].rstrip("\n"),
            )
        )
    return matches


def _search_python(query: str, root: str) -> list[SearchMatch]:
    matches = []
    query_lower = query.lower()
    for path in Path(root).rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (UnicodeDecodeError, PermissionError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if query_lower in line.lower():
                matches.append(
                    SearchMatch(file=str(path), line=line_number, text=line)
                )
    return matches`,

  "backend/tools/filesystem/write.py": String.raw`"""Write text contents to a file."""

from pathlib import Path


def write(file: str, content: str) -> None:
    """Write ` + BT + "content" + BT + " to " + BT + "file" + BT + String.raw`, creating parent directories as needed."""
    path = Path(file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")`,

  "backend/tests/test_read.py": String.raw`import pytest

from tools.filesystem import read


def test_reads_plain_text_utf8(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("hello world\nsecond line", encoding="utf-8")

    assert read(str(path)) == "hello world\nsecond line"


def test_reads_non_ascii_utf8(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("café ☃", encoding="utf-8")

    assert read(str(path)) == "café ☃"


def test_missing_file_raises_file_not_found(tmp_path):
    missing = tmp_path / "does_not_exist.txt"

    with pytest.raises(FileNotFoundError):
        read(str(missing))


def test_directory_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read(str(tmp_path))


def test_invalid_utf8_bytes_are_replaced_not_raised(tmp_path):
    path = tmp_path / "binary.txt"
    path.write_bytes(b"before\xffafter")

    result = read(str(path))

    assert "before" in result
    assert "after" in result


def test_reads_pdf(tmp_path):
    fitz = pytest.importorskip("fitz")

    path = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "hello from pdf")
    doc.save(str(path))
    doc.close()

    result = read(str(path))

    assert "hello from pdf" in result


def test_reads_docx(tmp_path):
    docx = pytest.importorskip("docx")

    path = tmp_path / "doc.docx"
    document = docx.Document()
    document.add_paragraph("first paragraph")
    document.add_paragraph("second paragraph")
    document.save(str(path))

    result = read(str(path))

    assert "first paragraph" in result
    assert "second paragraph" in result


def test_reads_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    path = tmp_path / "book.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["name", "count"])
    sheet.append(["widget", 3])
    workbook.save(str(path))

    result = read(str(path))
    lines = result.splitlines()

    assert lines[0] == "name\tcount"
    assert lines[1] == "widget\t3"


def test_xlsx_blank_cells_become_empty_string(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    path = tmp_path / "book.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["a", None, "c"])
    workbook.save(str(path))

    result = read(str(path))

    assert result.splitlines()[0] == "a\t\tc"


def test_suffix_dispatch_is_case_insensitive(tmp_path):
    fitz = pytest.importorskip("fitz")

    path = tmp_path / "doc.PDF"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "uppercase extension")
    doc.save(str(path))
    doc.close()

    result = read(str(path))

    assert "uppercase extension" in result


def test_unknown_extension_reads_as_plain_text(tmp_path):
    path = tmp_path / "data.custom"
    path.write_text("just text", encoding="utf-8")

    assert read(str(path)) == "just text"`,

  "backend/tests/test_search.py": String.raw`import importlib
import shutil

import pytest

from tools.filesystem import SearchMatch, search

# tools/filesystem/__init__.py does ` + BT + "from .search import search" + BT + String.raw`, which
# rebinds the ` + BT + "search" + BT + String.raw` attribute on the package to the function and shadows
# the submodule. Fetch the submodule via sys.modules (importlib) instead of
# ` + BT + "import tools.filesystem.search" + BT + String.raw`, which would resolve to that same
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

    assert called["ripgrep"] is False`,

  "backend/tests/test_write.py": String.raw`from tools.filesystem import write


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

    assert sibling.read_text(encoding="utf-8") == "sibling"`,
};
