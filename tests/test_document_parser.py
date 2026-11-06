from pathlib import Path

import pymupdf
import pytest

from sample_contracts.make_samples import make_pdf
from src.document_parser import MAX_PAGES, UnreadableDocument, parse_pdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LONG = "Distinctive filler sentence about employment terms. " * 8


def test_two_page_fixture():
    pages = parse_pdf((FIXTURES / "two_page.pdf").read_bytes())
    assert [p.number for p in pages] == [1, 2]
    assert "alpha-page-one" in pages[0].text
    assert "bravo-page-two" in pages[1].text


def test_empty_pages_omitted_keep_real_numbers():
    pages = parse_pdf(make_pdf([LONG, "   ", LONG + "third"]))
    assert [p.number for p in pages] == [1, 3]


def test_empty_bytes():
    with pytest.raises(UnreadableDocument):
        parse_pdf(b"")


def test_non_pdf_bytes():
    with pytest.raises(UnreadableDocument):
        parse_pdf(b"hello this is plain text, not a pdf")


def test_corrupt_pdf():
    data = (FIXTURES / "two_page.pdf").read_bytes()
    with pytest.raises(UnreadableDocument):
        parse_pdf(data[: len(data) // 3])


def test_password_protected():
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), LONG)
    data = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner"
    )
    doc.close()
    with pytest.raises(UnreadableDocument) as e:
        parse_pdf(data)
    assert "password" in str(e.value).lower()


def test_blank_pdf_mentions_scanned():
    with pytest.raises(UnreadableDocument) as e:
        parse_pdf((FIXTURES / "blank.pdf").read_bytes())
    assert "scanned" in str(e.value).lower()


def test_short_text_mentions_scanned_without_content():
    with pytest.raises(UnreadableDocument) as e:
        parse_pdf(make_pdf(["zebra-secret-phrase"]))
    assert "scanned" in str(e.value).lower()
    assert "zebra-secret-phrase" not in str(e.value)


def test_too_many_pages():
    assert MAX_PAGES == 40
    with pytest.raises(UnreadableDocument) as e:
        parse_pdf(make_pdf(["quokka-secret-phrase " + LONG] * (MAX_PAGES + 1)))
    assert "shorter" in str(e.value).lower()
    assert "quokka-secret-phrase" not in str(e.value)


def test_forty_pages_ok():
    assert len(parse_pdf(make_pdf([LONG] * MAX_PAGES))) == MAX_PAGES
