"""Build the fictional sample set. No real personal data."""

from pathlib import Path

from docx import Document
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent


def write_pdf(path: Path, text: str) -> None:
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 700 Td ({safe}) Tj ET\n".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("ascii")
        out += body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(out))


def write_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(path)


def write_salary(path: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "Payroll"
    sheet.append(["Employee", "Role", "Band", "Bonus"])
    for _ in range(13):
        sheet.append([None, None, None, None])
    sheet["A14"] = "Rahul Verma"
    sheet["B14"] = "Analyst"
    sheet["C14"] = "L4"
    sheet["D14"] = "1,50,000"
    sheet["A15"] = "Anita Shah"
    sheet["B15"] = "Analyst"
    sheet["C15"] = "L4"
    sheet["D15"] = "1,80,000"
    book.save(path)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    write_docx(
        ROOT / "northwind_v1.docx",
        [
            "NORTHWIND SUPPLIES VENDOR CONTRACT. Version 1.",
            "The Northwind contract notice period is 30 days.",
            "Payment terms are net 45 days.",
        ],
    )
    write_docx(
        ROOT / "northwind_v2.docx",
        [
            "NORTHWIND SUPPLIES VENDOR CONTRACT. Version 2.",
            "The Northwind contract notice period is 60 days.",
            "Payment terms are net 45 days.",
        ],
    )
    write_salary(ROOT / "fy25_payroll.xlsx")
    write_pdf(ROOT / "board_retention.pdf", "Board papers have a retention period of 7 years.")
    (ROOT / "leave_policy.scan.txt").write_text(
        "OCR_CONFIDENCE=0.62\nAn employee may take 18 days of leave.\n",
        encoding="utf-8",
    )
    print("wrote", ROOT)


if __name__ == "__main__":
    main()
