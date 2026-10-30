import json
from pathlib import Path

import pytest

from scripts.fetch_mom import FetchError, fetch_all, fetch_page, html_to_text

FIXTURE = Path(__file__).parent / "fixtures" / "mini_mom.html"


class Resp:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code


def stub(text, status=200, calls=None):
    def get(url, **kwargs):
        if calls is not None:
            calls.append((url, kwargs))
        return Resp(text, status)

    return get


def test_html_to_text_structure():
    out = html_to_text(FIXTURE.read_text(encoding="utf-8"))
    lines = out.splitlines()
    assert "# Annual leave" in lines
    assert "# How much leave" in lines
    assert "- Leave is pro-rated for part years" in lines
    assert "1st | 7" in lines
    assert any("paid annual leave" in ln for ln in lines)
    for junk in ("NAVIGATION", "FOOTER", "SCRIPT TEXT", "trackingJunk", "Share this page", "RELATED LINKS"):
        assert junk not in out
    assert "\n\n" not in out


def test_fallback_to_body():
    html = "<html><body><nav>NAV</nav><h1>Title</h1><p>Body text</p></body></html>"
    out = html_to_text(html)
    assert "# Title" in out and "Body text" in out and "NAV" not in out


def test_fetch_page_ok_and_request_args():
    calls = []
    html = FIXTURE.read_text(encoding="utf-8")
    # ensure converted text is long enough
    text = fetch_page("http://x/y", get=stub(html, calls=calls))
    assert "# Annual leave" in text
    url, kw = calls[0]
    assert url == "http://x/y"
    assert kw["timeout"] == 20
    assert kw["headers"]["User-Agent"] == "sg-contract-checker-capstone"


def test_fetch_page_403():
    with pytest.raises(FetchError) as e:
        fetch_page("http://x/y", get=stub("", 403))
    assert "http://x/y" in str(e.value) and "403" in str(e.value)


def test_fetch_page_too_short():
    with pytest.raises(FetchError, match="JavaScript"):
        fetch_page("http://x/y", get=stub("<html><body><p>hi</p></body></html>"))


def test_fetch_all(tmp_path):
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps([
        {"file": "a.txt", "kind": "web", "title": "A", "url": "http://x/a", "fetch": True},
        {"file": "b.txt", "kind": "web", "title": "B", "url": "http://x/b", "fetch": False},
    ]))
    out = tmp_path / "out"
    out.mkdir()
    html = FIXTURE.read_text(encoding="utf-8")
    written = fetch_all(str(manifest), str(out), get=stub(html))
    assert written == ["a.txt"]
    assert (out / "a.txt").read_text(encoding="utf-8").startswith("# Annual leave")
    assert not (out / "b.txt").exists()
