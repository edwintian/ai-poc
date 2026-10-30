from pathlib import Path

import pytest

from scripts.act_html_to_text import act_html_to_text

FIXTURE = Path(__file__).parent / "fixtures" / "mini_act.html"


@pytest.fixture(scope="module")
def text():
    return act_html_to_text(FIXTURE.read_text(encoding="utf-8"))


def test_headings_in_order(text):
    heads = [ln for ln in text.splitlines() if ln.startswith("# ")]
    assert [h.split()[1] for h in heads] == ["21.", "38.", "88A."]
    assert "# 38. Hours of work" in heads
    assert "# 88A. Annual leave" in heads


def section(text, num):
    parts = text.split("\n# ")
    return next(p for p in parts if p.lstrip("# ").startswith(num))


def test_s38_body(text):
    body = section(text, "38.")
    assert "44 hours in one week" in body
    assert "one and a half times" in body


def test_markers_start_lines(text):
    lines = [ln for ln in section(text, "38.").splitlines()]
    assert any(ln.startswith("(a)") for ln in lines)
    assert any(ln.startswith("(b)") for ln in lines)


def test_clean(text):
    assert "\xa0" not in text and "&nbsp;" not in text
    assert "<" not in text and ">" not in text
    assert "  " not in text


def test_no_sections():
    with pytest.raises(ValueError):
        act_html_to_text("<html><body><p>nothing</p></body></html>")
