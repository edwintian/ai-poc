import pymupdf

from src.schemas import Page

MAX_PAGES = 40
MIN_TEXT_CHARS = 200


class UnreadableDocument(Exception):
    """Raised with a short, user-safe message (never includes file content)."""


def parse_pdf(data: bytes) -> list[Page]:
    if not data:
        raise UnreadableDocument("The uploaded file is empty.")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise UnreadableDocument(
            "This file could not be read as a PDF. Please upload a valid PDF."
        ) from None
    try:
        if doc.needs_pass:
            raise UnreadableDocument(
                "This PDF is password-protected. Please upload an unlocked copy."
            )
        if doc.page_count > MAX_PAGES:
            raise UnreadableDocument(
                f"This document has more than {MAX_PAGES} pages. "
                "Please upload a shorter document."
            )
        pages = []
        try:
            for i, page in enumerate(doc, start=1):
                text = page.get_text().strip()
                if text:
                    pages.append(Page(number=i, text=text))
        except Exception:
            raise UnreadableDocument(
                "This PDF appears to be damaged and could not be read."
            ) from None
    finally:
        doc.close()
    if sum(len(p.text) for p in pages) < MIN_TEXT_CHARS:
        raise UnreadableDocument(
            "This PDF has little or no readable text. It may be a scanned "
            "document; please upload a text-based PDF."
        )
    return pages
