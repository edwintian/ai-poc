"""Generate PDFs with PyMuPDF (test fixtures now; sample contracts later)."""
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

TWO_PAGE = [
    "Employment Agreement. This agreement is made between Acme Pte Ltd and the "
    "Employee. The Employee shall be paid a monthly salary on the last working "
    "day of each month. Phrase alpha-page-one.",
    "Termination. Either party may terminate this agreement by giving one month "
    "written notice. The Employee shall keep all company information "
    "confidential. Phrase bravo-page-two.",
]


def make_pdf(pages: list[str]) -> bytes:
    """Return a text PDF with one page per string."""
    doc = pymupdf.open()
    try:
        for text in pages:
            page = doc.new_page()
            page.insert_textbox(pymupdf.Rect(50, 50, 545, 790), text, fontsize=11)
        return doc.tobytes()
    finally:
        doc.close()


def write_fixtures(out_dir: Path = FIXTURES) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "two_page.pdf").write_bytes(make_pdf(TWO_PAGE))
    (out_dir / "blank.pdf").write_bytes(make_pdf([""]))


if __name__ == "__main__":
    write_fixtures()
    print("wrote fixtures to", FIXTURES, file=sys.stderr)
