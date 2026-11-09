"""Read PDF, Word, Excel, plain text, and a scan with an OCR confidence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

OCR_LINE = re.compile(r"^OCR_CONFIDENCE\s*=\s*([0-9]*\.?[0-9]+)\s*$", re.I)


@dataclass
class Page:
    doc_id: str
    path: str
    locator: str
    text: str
    ocr_confidence: float | None = None


@dataclass
class Corpus:
    pages: list[Page] = field(default_factory=list)

    @property
    def doc_ids(self) -> list[str]:
        seen = []
        for page in self.pages:
            if page.doc_id not in seen:
                seen.append(page.doc_id)
        return seen


def _read_text(path: Path) -> tuple[str, float | None]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    confidence = None
    if lines:
        match = OCR_LINE.match(lines[0].strip())
        if match:
            confidence = float(match.group(1))
            raw = "\n".join(lines[1:]).strip()
    return raw, confidence


def _read_docx(path: Path) -> list[tuple[str, str]]:
    from docx import Document

    document = Document(str(path))
    blocks = []
    for index, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text.strip()
        if text:
            blocks.append((f"p{index}", text))
    return blocks


def _read_pdf(path: Path) -> list[tuple[str, str]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    blocks = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            blocks.append((f"page {index}", text))
    return blocks


def _read_xlsx(path: Path) -> list[tuple[str, str]]:
    from openpyxl import load_workbook

    book = load_workbook(path, data_only=True, read_only=True)
    blocks = []
    try:
        for sheet in book.worksheets:
            rows = list(sheet.iter_rows(values_only=False))
            if not rows:
                continue
            headers = []
            for cell in rows[0]:
                headers.append("" if cell.value is None else str(cell.value).strip())
            for row in rows[1:]:
                parts = []
                for cell in row:
                    if cell.value is None or str(cell.value).strip() == "":
                        continue
                    header = ""
                    if cell.column and cell.column - 1 < len(headers):
                        header = headers[cell.column - 1]
                    label = f"{header} " if header else ""
                    parts.append(f"{sheet.title}!{cell.coordinate}={label}{cell.value}")
                if parts:
                    blocks.append((f"{sheet.title}", " | ".join(parts)))
    finally:
        book.close()
    return blocks


def load_path(path: Path) -> list[Page]:
    path = Path(path)
    doc_id = path.name
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        blocks = _read_pdf(path)
        confidence = None
    elif suffix == ".docx":
        blocks = _read_docx(path)
        confidence = None
    elif suffix == ".xlsx":
        blocks = _read_xlsx(path)
        confidence = None
    elif suffix in {".txt", ".md"} or path.name.endswith(".scan.txt"):
        text, confidence = _read_text(path)
        blocks = [("page 1", text)] if text else []
    else:
        raise ValueError(f"unsupported file: {path.name}")
    return [
        Page(doc_id=doc_id, path=str(path), locator=locator, text=text, ocr_confidence=confidence)
        for locator, text in blocks
        if text.strip()
    ]


def source_files(folder: Path) -> list[Path]:
    folder = Path(folder)
    found = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or ".sourcedesk" in path.parts:
            continue
        if path.suffix.lower() in {".pdf", ".docx", ".xlsx", ".txt", ".md"} or path.name.endswith(".scan.txt"):
            found.append(path)
    return found


def load_dir(folder: Path) -> Corpus:
    pages: list[Page] = []
    for path in source_files(folder):
        pages.extend(load_path(path))
    return Corpus(pages=pages)
