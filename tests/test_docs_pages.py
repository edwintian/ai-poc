import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
ABOUT = str(ROOT / "pages" / "about.py")
METHOD = str(ROOT / "pages" / "methodology.py")


def md_text(at):
    return "\n".join(m.value for m in at.markdown)


def charts(at):
    return [e.proto.spec for e in at.get("graphviz_chart")]


def test_about_renders_with_required_content():
    at = AppTest.from_file(ABOUT).run()
    assert not at.exception
    text = md_text(at)
    for url in (
        "https://sso.agc.gov.sg/Act/EmA1968",
        "https://www.mom.gov.sg/employment-practices",
        "https://www.mom.gov.sg/employment-practices/contract-of-service",
    ):
        assert url in text
    assert "not a substitute for professional legal advice" in text
    assert "confidentiality" in text.lower() and "non-compete" in text.lower()


def test_methodology_charts_and_subheaders():
    at = AppTest.from_file(METHOD).run()
    assert not at.exception
    subs = [s.value for s in at.subheader]
    assert "Use Case 1: Contract Health Check" in subs
    assert "Use Case 2: Ask Your Contract" in subs
    assert "Safeguards" in subs
    specs = charts(at)
    assert len(specs) == 2
    for s in ("Extract terms", "Verify quotes", "Recover", "Rules engine",
              "Assess term", "Evidence check", "Findings report"):
        assert s in specs[0]
    for s in ("Retrieve (same pipeline)", "Answerable and cites a retrieved passage?",
              "Refuse", "Grounded answer"):
        assert s in specs[1]


def test_methodology_lists_all_adrs_by_number_and_title():
    at = AppTest.from_file(METHOD).run()
    text = md_text(at)
    files = sorted((ROOT / "docs" / "adr").glob("[0-9]*.md"))
    assert len(files) == 12
    for f in files:
        first = f.read_text(encoding="utf-8").splitlines()[0]
        num, title = re.match(r"# (\d{4}) – (.*)", first).groups()
        assert f"{num}" in text and title in text
