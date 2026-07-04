import pytest

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

    assert read(str(path)) == "just text"
