"""Read the text contents of a file, regardless of format."""

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
    return "\n".join(lines)
